# src/xrate/adapters/telegram/jobs.py
"""
Telegram Jobs - Scheduled Tasks and Background Processing

This module handles scheduled tasks and background processing for the bot.
It implements the main posting job that monitors market changes and posts
updates to the Telegram channel based on configurable percentage thresholds.

Files that USE this module:
- xrate.app (post_rate_job function is registered as scheduled task)

Files that this module USES:
- xrate.adapters.formatting.formatter (format_persian_market_update, format_persian_daily_report)
- xrate.application.rates_service (get_irr_snapshot)
- xrate.application.state_manager (state_manager for state management)
- xrate.application.stats (stats_tracker for statistics)
- xrate.adapters.persistence.admin_store (admin_store for admin user ID)
- xrate.config (settings for thresholds and channel configuration)
- xrate.adapters.providers.wallex (WallexProvider for Tether data)
"""
from __future__ import annotations  # Enable postponed evaluation of annotations
from dataclasses import dataclass  # Decorator for creating data classes
from typing import Optional  # Type hints for optional values
from datetime import datetime, timezone, time, timedelta  # Date/time utilities for timestamps and scheduling
import logging  # Standard library for logging messages
import asyncio  # Asynchronous programming support for async/await
from decimal import Decimal, ROUND_HALF_UP  # Precise decimal arithmetic for financial calculations

from telegram.ext import ContextTypes  # type: ignore[import-untyped]  # Telegram bot context type for job callbacks
from telegram.error import RetryAfter, TimedOut  # type: ignore[import-untyped]  # Telegram API rate limit and timeout exceptions

from xrate.adapters.formatting.formatter import format_persian_market_update, format_persian_daily_report  # Message formatting functions
from xrate.application.rates_service import get_irr_snapshot  # Business logic for exchange rates
from xrate.application.state_manager import state_manager  # State persistence singleton
from xrate.application.stats import stats_tracker  # Statistics tracking singleton
from xrate.adapters.persistence.admin_store import admin_store  # Admin user ID storage
from xrate.adapters.providers.wallex import WallexProvider  # Wallex API provider for Tether data
from xrate.adapters.ai.avalai import AvalaiService  # AI-powered market analysis service
from xrate.config import settings  # Application configuration and settings


# Hysteresis state: track last breach direction per instrument to prevent flip-flop
_breach_history: dict[str, Optional[str]] = {}  # key: instrument, value: "up"/"down"/None


def _breach(curr: float, prev: float, up_pct: float, down_pct: float, instrument: str = "") -> bool:
    """
    Check if current value has breached the threshold compared to previous value.
    Uses Decimal for precise calculations and implements hysteresis to prevent flip-flop.
    
    Logic:
    - Increase breach: curr >= prev * (1 + up_pct/100)   [e.g., +1% threshold]
    - Decrease breach: curr <= prev * (1 - down_pct/100)  [e.g., -2% threshold]
    - Hysteresis: After first breach, require +0.2% extra movement before posting again
    
    Args:
        curr: Current value
        prev: Previous/baseline value
        up_pct: Percentage threshold for increase (e.g., 1.0 means 1% increase triggers)
        down_pct: Percentage threshold for decrease (e.g., 2.0 means 2% decrease triggers)
        instrument: Optional instrument name for hysteresis tracking (e.g., "usd", "eur")
        
    Returns:
        True if threshold is breached (increase >= up_pct OR decrease >= down_pct), False otherwise
        Always returns True if prev <= 0 (no valid baseline)
    """
    if prev <= 0:
        return True  # no baseline → always announce
    
    # Use Decimal for precise floating-point calculations
    curr_decimal = Decimal(str(curr)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    prev_decimal = Decimal(str(prev)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    up_pct_decimal = Decimal(str(up_pct)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    down_pct_decimal = Decimal(str(down_pct)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Calculate thresholds with Decimal precision
    upper_bound = prev_decimal * (Decimal('1.0') + up_pct_decimal / Decimal('100.0'))
    lower_bound = prev_decimal * (Decimal('1.0') - down_pct_decimal / Decimal('100.0'))
    
    # Check basic breach conditions
    increase_breach = curr_decimal >= upper_bound
    decrease_breach = curr_decimal <= lower_bound
    
    # Apply hysteresis if we have a previous breach state for this instrument
    if instrument and instrument in _breach_history:
        last_direction = _breach_history[instrument]
        if last_direction == "up" and increase_breach:
            # After an upward breach, require +0.2% extra movement before posting again
            hysteresis_upper = upper_bound * Decimal('1.002')  # +0.2% buffer
            if curr_decimal < hysteresis_upper:
                return False  # Don't breach yet, still in hysteresis zone
        elif last_direction == "down" and decrease_breach:
            # After a downward breach, require -0.2% extra movement before posting again
            hysteresis_lower = lower_bound * Decimal('0.998')  # -0.2% buffer
            if curr_decimal > hysteresis_lower:
                return False  # Don't breach yet, still in hysteresis zone
    
    # Update breach history if there's a breach
    if instrument:
        if increase_breach:
            _breach_history[instrument] = "up"
        elif decrease_breach:
            _breach_history[instrument] = "down"
        else:
            # No breach - reset history after significant movement away from threshold
            # Only reset if we're well away from the threshold (e.g., >0.5% away)
            percent_change = ((curr_decimal - prev_decimal) / prev_decimal) * Decimal('100.0')
            if abs(percent_change) < Decimal('0.5'):
                # Still near threshold, keep history
                pass
            else:
                # Moved well away, reset
                _breach_history[instrument] = None
    
    return increase_breach or decrease_breach


def _breach_tether_24h_ch(tether_24h_ch: float, up_pct: float, down_pct: float) -> bool:
    """
    Check if Tether 24h_ch has breached the threshold.
    
    For Tether, we check the signed 24h_ch against thresholds:
    - Positive changes (gains) trigger if >= up_pct
    - Negative changes (losses) trigger if <= -down_pct (e.g., -2.2% triggers if down_pct=2.0)
    
    Args:
        tether_24h_ch: 24-hour change percentage from Wallex API (can be negative)
        up_pct: Upper threshold percentage (e.g., 1.0 means 1% increase triggers)
        down_pct: Lower threshold percentage (e.g., 2.0 means 2% decrease triggers)
        
    Returns:
        True if tether_24h_ch >= up_pct OR tether_24h_ch <= -down_pct, False otherwise
    """
    # Check both directions: positive changes vs upper threshold, negative vs lower threshold
    increase_breach = tether_24h_ch >= up_pct
    decrease_breach = tether_24h_ch <= -down_pct
    return increase_breach or decrease_breach


# Re-entrancy protection: ensure only one job runs at a time
_post_rate_job_lock = asyncio.Lock()

# Avalai service instance (initialized lazily)
_avalai_service: Optional[AvalaiService] = None

def _get_avalai_service() -> Optional[AvalaiService]:
    """
    Get or create Avalai service instance for AI-powered market analysis.
    
    Uses lazy initialization to create the service only when needed.
    Returns None if API key is not configured.
    
    Returns:
        AvalaiService instance if configured, None otherwise
    """
    global _avalai_service
    if _avalai_service is None:
        _avalai_service = AvalaiService()
    return _avalai_service

# Per-provider next-eligible time tracking (to respect individual TTLs)
_provider_next_eligible: dict[str, datetime] = {}


def _should_fetch_provider(provider_name: str, cache_minutes: int) -> bool:
    """
    Check if a provider should be fetched based on its individual TTL.
    
    Tracks per-provider next-eligible time to prevent fetching providers more frequently
    than their intended cadence, even when the job runs at the minimum TTL interval.
    This prevents rate limiting on providers with longer cache windows.
    
    Args:
        provider_name: Name of the provider (e.g., "navasan", "wallex", "crawler1_bonbast", "crawler2_alanchand")
        cache_minutes: Cache TTL in minutes for this provider
        
    Returns:
        True if provider should be fetched (TTL has elapsed), False if it's too soon
        
    Example:
        If Navasan has 28-minute TTL but job runs every 15 minutes, this ensures
        Navasan is only fetched once every 28 minutes, not every job cycle.
    """
    now = datetime.now(timezone.utc)
    if provider_name not in _provider_next_eligible:
        # First time, allow fetch
        _provider_next_eligible[provider_name] = now
        return True
    
    next_eligible = _provider_next_eligible[provider_name]
    if now >= next_eligible:
        # Update next eligible time
        _provider_next_eligible[provider_name] = now + timedelta(minutes=cache_minutes)
        return True
    
    # Too soon, skip this provider
    logger = logging.getLogger(__name__)
    logger.debug("Skipping %s fetch - next eligible at %s (TTL: %d min)", 
                 provider_name, next_eligible, cache_minutes)
    return False


async def post_rate_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Scheduled job that monitors market changes and posts updates to Telegram channel.
    
    This function:
    1. Fetches current market data from crawlers (with Navasan fallback)
    2. Compares with last posted values using consolidated thresholds
    3. Posts to channel if any threshold is breached (Persian format)
    4. Updates state baseline after posting
    
    Includes re-entrancy protection to prevent concurrent execution.
    
    Args:
        context: Telegram bot context
    """
    global _post_rate_job_lock
    logger = logging.getLogger(__name__)
    
    # Re-entrancy protection: skip if job is already running
    if _post_rate_job_lock.locked():
        logger.warning("post_rate_job: Skipping concurrent execution (previous job still running)")
        return
    
    # Acquire lock for this execution
    async with _post_rate_job_lock:
        # Fetch IRR snapshot from crawlers (with Navasan fallback)
        snap = get_irr_snapshot()
        
        # Check if we have data
        if snap is None:
            logger.warning("All data sources unavailable - skipping job run")
            return
        
        # Get current timestamp and state (used throughout the function)
        now = datetime.now(timezone.utc)
        current_state = state_manager.get_current_state()
        
        logger.debug("Fetched rates: USD=%d, EUR=%d, Gold=%d", 
                    snap.usd_toman, snap.eur_toman, snap.gold_1g_toman)

        # First run after (re)start: post without % (no baseline), then set baseline
        if current_state is None:
            try:
                logger.info("First run - posting initial market data")
                
                # Use Persian daily report format for first run
                elapsed_seconds = 0
                text = format_persian_daily_report(snap, elapsed_seconds)
                
                try:
                    await context.bot.send_message(
                        chat_id=settings.channel_id,
                        text=text,
                    )
                except RetryAfter as e:
                    logger.warning("Telegram rate limit (429): retry after %s seconds", e.retry_after)
                    await asyncio.sleep(float(e.retry_after) + 1)
                    await context.bot.send_message(
                        chat_id=settings.channel_id,
                        text=text,
                    )
                except TimedOut:
                    logger.warning("Telegram request timed out, will retry on next job run")
                    raise
                
                # Track the post
                provider_name = snap.provider if snap.provider else "unknown"
                stats_tracker.record_post(providers=[provider_name], is_manual=False)
                
                # Update state
                state_manager.update_state(
                    usd_toman=snap.usd_toman,
                    eur_toman=snap.eur_toman,
                    gold_1g_toman=snap.gold_1g_toman,
                    eurusd_rate=0.0,  # No longer used, but keep for compatibility
                    tether_price_toman=0,
                    tether_24h_ch=0.0,
                    ts=now,
                )
                logger.info("Initial baseline set and persisted")
            except Exception as e:
                logger.error("Failed to post initial message: %s", e)
            return

        # Compare against last announced using consolidated thresholds
        # USD and EUR use margin_currency_upper/lower_pct
        # Gold uses margin_gold_upper/lower_pct
        trigger_usd = False
        trigger_eur = False
        trigger_gold = False
        
        if snap:
            trigger_usd = _breach(
                snap.usd_toman, current_state.usd_toman,
                settings.margin_currency_upper_pct, settings.margin_currency_lower_pct,
                instrument="usd",
            ) if current_state.usd_toman > 0 else True
            
            trigger_eur = _breach(
                snap.eur_toman, current_state.eur_toman,
                settings.margin_currency_upper_pct, settings.margin_currency_lower_pct,
                instrument="eur",
            ) if current_state.eur_toman > 0 else True
            
            trigger_gold = _breach(
                snap.gold_1g_toman, current_state.gold_1g_toman,
                settings.margin_gold_upper_pct, settings.margin_gold_lower_pct,
                instrument="gold",
            ) if current_state.gold_1g_toman > 0 else True

        elapsed_seconds = state_manager.get_elapsed_seconds()
        
        logger.debug("Threshold check: USD=%s, EUR=%s, Gold=%s", 
                    trigger_usd, trigger_eur, trigger_gold)

        # Only post if any threshold is breached
        if trigger_usd or trigger_eur or trigger_gold:
            try:
                logger.info("Threshold breached - posting update to channels")
                
                # Build Persian message with changes (generate once)
                text = format_persian_market_update(
                    curr=snap,
                    prev_usd_toman=current_state.usd_toman,
                    prev_eur_toman=current_state.eur_toman,
                    prev_gold_1g_toman=current_state.gold_1g_toman,
                    elapsed_seconds=elapsed_seconds,
                )
                
                # Generate Avalai analysis once (if configured) - reduces API calls
                analysis_text = None
                try:
                    avalai = _get_avalai_service()
                    if avalai and avalai.client:
                        try:
                            analysis_text = await asyncio.wait_for(
                                avalai.generate_analysis(price_message=text),
                                timeout=30.0
                            )
                        except asyncio.TimeoutError:
                            logger.warning("Avalai API call timed out - skipping analysis")
                        except Exception as e:
                            logger.warning("Avalai analysis failed (non-blocking): %s", e)
                except Exception as e:
                    logger.debug("Avalai service not available: %s", e)
                
                # Post to main channel (same message)
                channels_posted = []
                try:
                    await context.bot.send_message(
                        chat_id=settings.channel_id,
                        text=text,
                    )
                    channels_posted.append("main")
                    logger.info("Posted to main channel")
                except RetryAfter as e:
                    logger.warning("Telegram rate limit (429): retry after %s seconds", e.retry_after)
                    wait_time = float(e.retry_after) + 1
                    await asyncio.sleep(wait_time)
                    await context.bot.send_message(
                        chat_id=settings.channel_id,
                        text=text,
                    )
                    channels_posted.append("main")
                except TimedOut:
                    logger.warning("Telegram request timed out for main channel")
                
                # Post to test channel if configured (same message - reduces API calls)
                if settings.test_channel_id:
                    try:
                        await context.bot.send_message(
                            chat_id=settings.test_channel_id,
                            text=text,
                        )
                        channels_posted.append("test")
                        logger.info("Posted to test channel")
                    except Exception as e:
                        logger.warning("Failed to post to test channel: %s", e)
                
                # Post Avalai analysis to both channels if available (same analysis - reduces API calls)
                if analysis_text:
                    for channel_id in [settings.channel_id, settings.test_channel_id]:
                        if channel_id:
                            try:
                                await context.bot.send_message(
                                    chat_id=channel_id,
                                    text=analysis_text,
                                )
                            except Exception as e:
                                logger.warning("Failed to post Avalai analysis to channel %s: %s", channel_id, e)
                
                # Track the post
                provider_name = snap.provider if snap.provider else "unknown"
                stats_tracker.record_post(providers=[provider_name], is_manual=False)
                
                # Update state
                state_manager.update_state(
                    usd_toman=snap.usd_toman,
                    eur_toman=snap.eur_toman,
                    gold_1g_toman=snap.gold_1g_toman,
                    eurusd_rate=0.0,  # No longer used
                    tether_price_toman=0,
                    tether_24h_ch=0.0,
                    ts=now,
                )
                logger.info("New baseline set and persisted (posted to: %s)", ", ".join(channels_posted))
            except Exception as e:
                logger.error("Failed to post message to channel: %s", e)
                stats_tracker.record_error(str(e))
        else:
            logger.debug("No threshold breached - skipping post")


async def startup_notification(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send startup notification to admin with bot configuration and commands.
    
    This function is called once when the bot starts to inform the admin:
    - Bot has started
    - Target channel
    - Posting interval
    - Configuration summary
    - Available commands
    """
    logger = logging.getLogger(__name__)
    
    admin_user_id = admin_store.get_admin_user_id()
    
    # If no stored admin ID, try to get it from username via bot API
    if not admin_user_id:
        admin_username = settings.admin_username.lstrip("@")
        try:
            # Try to get chat info by username (this works if user has interacted with bot)
            chat = await context.bot.get_chat(chat_id=f"@{admin_username}")
            if chat and chat.id:
                admin_user_id = chat.id
                admin_store.set_admin_user_id(admin_user_id)
                logger.info("Resolved admin user ID from username: %s -> %s", admin_username, admin_user_id)
            else:
                logger.warning("Could not resolve admin username to user ID. Admin should use a command to register their ID.")
                return
        except Exception as e:
            logger.warning("Failed to get admin user ID from username '%s': %s. Admin should use a command to register their ID.", admin_username, e)
            return
    
    if not admin_user_id:
        logger.warning("No admin user ID available - skipping startup notification")
        return
    
    try:
        # Build configuration summary
        calculated_interval = settings.post_interval_minutes
        config_summary = f"""🔧 **Configuration Summary**
• Post Interval: {calculated_interval} minutes (auto-calculated: min of cache TTLs)
• HTTP Timeout: {settings.http_timeout_seconds} seconds

📊 **Thresholds**
• Currency (USD/EUR): ↑{settings.margin_currency_upper_pct}% / ↓{settings.margin_currency_lower_pct}%
• Gold: ↑{settings.margin_gold_upper_pct}% / ↓{settings.margin_gold_lower_pct}%

💾 **Cache Settings**
• Navasan: {settings.navasan_cache_minutes} min
• Wallex: {settings.wallex_cache_minutes} min
• Crawler1 (Bonbast): {settings.crawler1_interval_minutes} min
• Crawler2 (AlanChand): {settings.crawler2_interval_minutes} min"""

        # Build commands list
        commands_list = """📋 **Available Commands**
• `/start` - Get current market data (Admin only)
• `/irr` - Get Iranian market snapshot (Admin only)
• `/health` - Check system health (Admin only)
• `/post` - Manually post to main channel (Admin)
• `/posttest` - Manually post to test channel (Admin)
• `/language` - Change bot language (Admin)"""

        message = f"""✅ **Bot Started Successfully**

📢 **Channel**: `{settings.channel_id}`
⏰ **Post Interval**: Every {calculated_interval} minutes (calculated as min of cache TTLs)

{config_summary}

{commands_list}

🤖 Bot is now monitoring the market and will post updates when thresholds are breached."""
        
        await context.bot.send_message(
            chat_id=admin_user_id,
            text=message,
            parse_mode="Markdown",
        )
        logger.info("Startup notification sent to admin")
    except Exception as e:
        logger.error("Failed to send startup notification: %s", e)


async def crawler1_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Scheduled job for Crawler1 (Bonbast) to fetch prices every configured interval.
    
    Fetches USD, EUR, and GoldGram sell prices from bonbast.com and logs the results.
    The crawler has built-in caching to prevent too frequent requests.
    
    Args:
        context: Telegram bot context (not used but required by job queue)
    """
    logger = logging.getLogger(__name__)
    
    try:
        from xrate.adapters.crawlers.bonbast_crawler import BonbastCrawler
        from xrate.config import settings
        
        crawler = BonbastCrawler(
            url=settings.crawler1_url,
            cache_minutes=settings.crawler1_interval_minutes,
            timeout=settings.http_timeout_seconds,
        )
        
        result = crawler.fetch()
        
        logger.info(
            "Crawler1 (Bonbast) fetched: USD=%s, EUR=%s, GoldGram=%s",
            result.usd_sell,
            result.eur_sell,
            result.gold_gram_sell,
        )
        
        # Log warning if any prices are missing
        if not result.usd_sell or not result.eur_sell or not result.gold_gram_sell:
            missing = []
            if not result.usd_sell:
                missing.append("USD")
            if not result.eur_sell:
                missing.append("EUR")
            if not result.gold_gram_sell:
                missing.append("GoldGram")
            logger.warning("Crawler1 (Bonbast) missing prices: %s", ", ".join(missing))
            
    except Exception as e:
        logger.error("Crawler1 (Bonbast) job failed: %s", e, exc_info=True)


async def crawler2_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Scheduled job for Crawler2 (AlanChand) to fetch prices every configured interval.
    
    Fetches USD, EUR, and GoldGram sell prices from alanchand.com and logs the results.
    The crawler has built-in caching to prevent too frequent requests.
    
    Args:
        context: Telegram bot context (not used but required by job queue)
    """
    logger = logging.getLogger(__name__)
    
    try:
        from xrate.adapters.crawlers.alanchand_crawler import AlanChandCrawler
        from xrate.config import settings
        
        crawler = AlanChandCrawler(
            url=settings.crawler2_url,
            cache_minutes=settings.crawler2_interval_minutes,
            timeout=settings.http_timeout_seconds,
        )
        
        result = crawler.fetch()
        
        logger.info(
            "Crawler2 (AlanChand) fetched: USD=%s, EUR=%s, GoldGram=%s",
            result.usd_sell,
            result.eur_sell,
            result.gold_gram_sell,
        )
        
        # Log warning if any prices are missing
        if not result.usd_sell or not result.eur_sell or not result.gold_gram_sell:
            missing = []
            if not result.usd_sell:
                missing.append("USD")
            if not result.eur_sell:
                missing.append("EUR")
            if not result.gold_gram_sell:
                missing.append("GoldGram")
            logger.warning("Crawler2 (AlanChand) missing prices: %s", ", ".join(missing))
            
    except Exception as e:
        logger.error("Crawler2 (AlanChand) job failed: %s", e, exc_info=True)


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send daily summary report to admin at scheduled time (9 PM UTC by default).
    
    Collects statistics from the last 24 hours and sends a formatted report to the admin user.
    Includes post counts (manual vs automatic), error counts, provider usage statistics,
    and overall activity metrics. Uses timezone-aware scheduling to handle DST transitions.
    
    The report is sent only if an admin user ID is available. If not available, the job
    silently skips execution.
    
    Args:
        context: Telegram bot context with access to bot API
    """
    logger = logging.getLogger(__name__)
    
    admin_user_id = admin_store.get_admin_user_id()
    if not admin_user_id:
        logger.debug("No admin user ID stored - skipping daily summary")
        return
    
    try:
        summary = stats_tracker.get_last_24h_summary()
        
        posts_sent = summary.get("posts_sent", 0)
        errors_count = summary.get("errors_count", 0)
        manual_posts = summary.get("manual_posts", 0)
        provider_usage = summary.get("provider_usage", {})
        
        # Format provider usage with Persian names
        from xrate.shared.language import translate_provider_name
        provider_text = ""
        if provider_usage:
            provider_items = []
            for provider, count in sorted(provider_usage.items(), key=lambda x: x[1], reverse=True):
                persian_name = translate_provider_name(provider)
                provider_items.append(f"• {persian_name}: {count}")
            provider_text = "\n".join(provider_items)
        else:
            provider_text = "• No provider usage data"
        
        # Get crawler usage times and counts
        from xrate.application.crawler_service import get_crawler_usage_times
        crawler1_time, crawler2_time = get_crawler_usage_times()
        crawler_usage_counts = summary.get("crawler_usage", {})
        crawler_info = ""
        if crawler1_time or crawler2_time or crawler_usage_counts:
            crawler1_str = crawler1_time.strftime("%Y-%m-%d %H:%M:%S UTC") if crawler1_time else "Never"
            crawler2_str = crawler2_time.strftime("%Y-%m-%d %H:%M:%S UTC") if crawler2_time else "Never"
            crawler1_count = crawler_usage_counts.get("crawler1_bonbast", 0)
            crawler2_count = crawler_usage_counts.get("crawler2_alanchand", 0)
            crawler_info = f"\n\n🕷️ **Crawler Usage**:\n• Crawler1 (Bonbast): {crawler1_count} times (Last: {crawler1_str})\n• Crawler2 (AlanChand): {crawler2_count} times (Last: {crawler2_str})"
        
        # Get feedback from today (last 24h)
        today = datetime.now(timezone.utc).date().isoformat()
        feedback_list = []
        if stats_tracker._stats and today in stats_tracker._stats.daily_stats:
            today_stats = stats_tracker._stats.daily_stats[today]
            if hasattr(today_stats, 'feedback') and today_stats.feedback:
                # Only include feedback from last 24 hours
                cutoff = datetime.now(timezone.utc).timestamp() - 86400
                for fb in today_stats.feedback:
                    try:
                        fb_time = datetime.fromisoformat(fb.timestamp.replace("Z", "+00:00"))
                        if fb_time.timestamp() >= cutoff:
                            feedback_list.append(fb)
                    except Exception:
                        pass  # Skip invalid timestamps
        
        # Format feedback
        feedback_text = ""
        if feedback_list:
            feedback_items = []
            for fb in feedback_list:
                timestamp_str = fb.timestamp[:16].replace('T', ' ') if fb.timestamp else "Unknown"
                feedback_items.append(f"• @{fb.username} ({timestamp_str}): {fb.message[:50]}...")
            feedback_text = "\n\n📝 **User Feedback**:\n" + "\n".join(feedback_items)
        
        # Get Avalai wallet value
        from xrate.application.health import health_checker
        avalai_wallet_status = health_checker.check_avalai_wallet()
        avalai_wallet_text = ""
        if avalai_wallet_status.is_healthy and avalai_wallet_status.details:
            wallet_credit = avalai_wallet_status.details.get("credit", "Unknown")
            avalai_wallet_text = f"\n\n💰 **Avalai Wallet**: {wallet_credit}"
        elif not avalai_wallet_status.is_healthy:
            avalai_wallet_text = f"\n\n💰 **Avalai Wallet**: {avalai_wallet_status.message}"
        
        # Get overall stats
        overall = stats_tracker.get_overall_stats()
        total_posts = overall.get("total_posts", 0)
        
        message = f"""📊 **Daily Summary** (Last 24 Hours)

📤 **Posts Sent**: {posts_sent}
   └─ Manual: {manual_posts}
   └─ Automatic: {posts_sent - manual_posts}
   └─ Total (all time): {total_posts}

❌ **Errors**: {errors_count}

🌐 **Provider Usage**:
{provider_text}{crawler_info}{feedback_text}{avalai_wallet_text}

🕐 Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"""
        
        await context.bot.send_message(
            chat_id=admin_user_id,
            text=message,
            parse_mode="Markdown",
        )
        logger.info("Daily summary sent to admin")
    except Exception as e:
        logger.error("Failed to send daily summary: %s", e)


async def daily_morning_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Daily morning post at 8:00 AM (excluding Thursday and Friday).
    
    Posts market data in Persian daily report format to main channel.
    """
    logger = logging.getLogger(__name__)
    
    # Check if today is Thursday (3) or Friday (4) - skip if so
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
    
    if weekday == 3 or weekday == 4:  # Thursday or Friday
        logger.info("Skipping daily morning post - today is %s (weekday=%d)", 
                   "Thursday" if weekday == 3 else "Friday", weekday)
        return
    
    try:
        snap = get_irr_snapshot()
        
        if snap is None:
            logger.warning("Daily morning post skipped - no market data available")
            return
        
        # Use Persian daily report format (generate once)
        elapsed_seconds = state_manager.get_elapsed_seconds()
        text = format_persian_daily_report(snap, elapsed_seconds)
        
        # Post to main channel
        channels_posted = []
        try:
            await context.bot.send_message(
                chat_id=settings.channel_id,
                text=text,
            )
            channels_posted.append("main")
        except Exception as e:
            logger.error("Failed to post to main channel: %s", e)
        
        # Post to test channel if configured (same message)
        if settings.test_channel_id:
            try:
                await context.bot.send_message(
                    chat_id=settings.test_channel_id,
                    text=text,
                )
                channels_posted.append("test")
            except Exception as e:
                logger.warning("Failed to post to test channel: %s", e)
        
        logger.info("Daily morning post sent to channels at 8:00 AM: %s", ", ".join(channels_posted))
        
        # Track the post
        provider_name = snap.provider if snap.provider else "unknown"
        stats_tracker.record_post(providers=[provider_name], is_manual=False)
        
    except Exception as e:
        logger.error("Failed to send daily morning post: %s", e, exc_info=True)
        stats_tracker.record_error(str(e))
