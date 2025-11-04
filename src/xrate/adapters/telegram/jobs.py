# src/xrate/adapters/telegram/jobs.py
"""
Telegram Jobs - Scheduled Tasks and Background Processing

This module handles scheduled tasks and background processing for the bot.
It implements the main posting job that monitors market changes and posts
updates to the Telegram channel based on configurable percentage thresholds.

Files that USE this module:
- xrate.app (post_rate_job function is registered as scheduled task)

Files that this module USES:
- xrate.adapters.formatting.formatter (market_lines, market_lines_with_changes)
- xrate.application.rates_service (RatesService, get_irr_snapshot)
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

from telegram.ext import ContextTypes  # Telegram bot context type for job callbacks
from telegram.error import RetryAfter, TimedOut  # Telegram API rate limit and timeout exceptions

from xrate.adapters.formatting.formatter import market_lines_with_changes, market_lines  # Message formatting functions
from xrate.application.rates_service import RatesService, get_irr_snapshot  # Business logic for exchange rates
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
        provider_name: Name of the provider (e.g., "brsapi", "fastforex", "navasan", "wallex")
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


async def post_rate_job(context: ContextTypes.DEFAULT_TYPE, svc: RatesService) -> None:
    """
    Scheduled job that monitors market changes and posts updates to Telegram channel.
    
    This function:
    1. Fetches current market data (EUR/USD rate and IRR snapshot) respecting per-provider TTLs
    2. Compares with last posted values using configured thresholds
    3. Posts to channel if any threshold is breached
    4. Updates state baseline after posting
    
    Includes re-entrancy protection to prevent concurrent execution.
    
    Args:
        context: Telegram bot context
        svc: RatesService instance for fetching exchange rates
    """
    global _post_rate_job_lock
    logger = logging.getLogger(__name__)
    
    # Re-entrancy protection: skip if job is already running
    if _post_rate_job_lock.locked():
        logger.warning("post_rate_job: Skipping concurrent execution (previous job still running)")
        return
    
    # Acquire lock for this execution
    async with _post_rate_job_lock:
        # Check if we should fetch EUR/USD (BRS/FastForex)
        eurusd_rate = None
        if _should_fetch_provider("brsapi", settings.brsapi_cache_minutes) or \
           _should_fetch_provider("fastforex", settings.fastforex_cache_minutes):
            eurusd_rate = svc.eur_usd()
        
        # Check if we should fetch IRR snapshot (BRS/Navasan)
        snap = None
        if _should_fetch_provider("brsapi", settings.brsapi_cache_minutes) or \
           _should_fetch_provider("navasan", settings.navasan_cache_minutes):
            snap = get_irr_snapshot()
        
        # Fetch Tether data from Wallex API (only if TTL allows)
        tether_price_toman: Optional[int] = None
        tether_24h_ch: Optional[float] = None
        if _should_fetch_provider("wallex", settings.wallex_cache_minutes):
            try:
                wallex_provider = WallexProvider()
                tether_data = wallex_provider.get_tether_data()
                if tether_data:
                    tether_price_toman = int(tether_data["price"])
                    tether_24h_ch = float(tether_data["24h_ch"])
                    logger.debug("Fetched Tether: price=%s, 24h_ch=%s%%", tether_price_toman, tether_24h_ch)
            except Exception as e:
                logger.warning("Failed to fetch Tether data from Wallex: %s", e)
        
        # Check if we have at least some data
        if eurusd_rate is None and snap is None:
            logger.warning("All data sources unavailable - skipping job run")
            return
        
        # Get current timestamp and state (used throughout the function)
        now = datetime.now(timezone.utc)
        current_state = state_manager.get_current_state()
        
        if snap:
            logger.debug("Fetched rates: EUR/USD=%s, USD=%d, EUR=%d, Gold=%d", 
                        eurusd_rate, snap.usd_toman, snap.eur_toman, snap.gold_1g_toman)
        else:
            logger.debug("Fetched rates: EUR/USD=%s, IRR data unavailable", eurusd_rate)

            # First run after (re)start: post without % (no baseline), then set baseline
            if current_state is None:
                try:
                    logger.info("First run - posting initial market data")
                    # Collect providers for first run
                    first_run_providers = []
                    if snap and snap.provider:
                        first_run_providers.append(snap.provider)
                    if eurusd_rate is not None:
                        eurusd_provider = svc.get_eur_usd_provider()
                        if eurusd_provider and eurusd_provider not in first_run_providers:
                            first_run_providers.append(eurusd_provider)
                    
                    try:
                        await context.bot.send_message(
                            chat_id=settings.channel_id,
                            text=market_lines(snap, eurusd_rate, providers=first_run_providers if first_run_providers else None),
                        )
                    except RetryAfter as e:
                        logger.warning("Telegram rate limit (429): retry after %s seconds", e.retry_after)
                        # Wait and retry once
                        await asyncio.sleep(float(e.retry_after) + 1)
                        await context.bot.send_message(
                            chat_id=settings.channel_id,
                            text=market_lines(snap, eurusd_rate, providers=first_run_providers if first_run_providers else None),
                        )
                    except TimedOut:
                        logger.warning("Telegram request timed out, will retry on next job run")
                        raise  # Re-raise to trigger outer exception handler
                    
                    # Generate and send analysis from Avalai API (first run)
                    # This is completely non-blocking - failures here never affect the main job
                    try:
                        logger.info("Starting Avalai analysis generation for first run post")
                        avalai = _get_avalai_service()
                        if avalai:
                            logger.info("Avalai service obtained for first run, checking client")
                            if avalai.client:
                                logger.info("Generating market analysis from Avalai API (first run)")
                                first_run_text = market_lines(snap, eurusd_rate, providers=first_run_providers if first_run_providers else None)
                                # Use asyncio timeout to prevent hanging on slow API
                                try:
                                    analysis = await asyncio.wait_for(
                                        avalai.generate_analysis(price_message=first_run_text),
                                        timeout=30.0  # 30 second timeout for Avalai API
                                    )
                                    if analysis:
                                        logger.info("First run analysis received (length=%d chars), sending to channel", len(analysis))
                                        await context.bot.send_message(
                                            chat_id=settings.channel_id,
                                            text=analysis,
                                        )
                                        logger.info("First run analysis sent to channel successfully")
                                    else:
                                        logger.warning("First run: No analysis generated from Avalai API (returned None)")
                                except asyncio.TimeoutError:
                                    logger.warning("First run: Avalai API call timed out after 30 seconds - analysis skipped")
                                except Exception as avalai_error:
                                    logger.warning("First run: Avalai API call failed (non-blocking): %s", avalai_error, exc_info=True)
                            else:
                                logger.warning("First run: Avalai client not initialized")
                        else:
                            logger.warning("First run: Avalai service not available")
                    except Exception as e:
                        # Catch-all for any unexpected errors - never fail the main job
                        logger.warning("First run: Unexpected error in Avalai analysis (non-blocking): %s", e, exc_info=True)
                    
                    # Track the post
                    stats_tracker.record_post(providers=first_run_providers, is_manual=False)
                    # Only update state if we have actual data
                    if snap or eurusd_rate is not None:
                        state_manager.update_state(
                            usd_toman=snap.usd_toman if snap else 0,
                            eur_toman=snap.eur_toman if snap else 0,
                            gold_1g_toman=snap.gold_1g_toman if snap else 0,
                            eurusd_rate=eurusd_rate if eurusd_rate is not None else 0.0,
                            tether_price_toman=tether_price_toman if tether_price_toman is not None else 0,
                            tether_24h_ch=tether_24h_ch if tether_24h_ch is not None else 0.0,
                            ts=now,
                        )
                    logger.info("Initial baseline set and persisted")
                except Exception as e:
                    logger.error("Failed to post initial message: %s", e)
                return

            # Compare against last announced using configured margins
            # Only check thresholds for data we actually have
            trigger_usd = False
            trigger_eur = False
            trigger_gold = False
            trigger_fx = False
            trigger_tether = False
            
            if snap:
                trigger_usd = _breach(
                    snap.usd_toman, current_state.usd_toman,
                        settings.margin_usd_upper_pct, settings.margin_usd_lower_pct,
                        instrument="usd",
                ) if current_state.usd_toman > 0 else True
                trigger_eur = _breach(
                    snap.eur_toman, current_state.eur_toman,
                        settings.margin_eur_upper_pct, settings.margin_eur_lower_pct,
                        instrument="eur",
                ) if current_state.eur_toman > 0 else True
                trigger_gold = _breach(
                    snap.gold_1g_toman, current_state.gold_1g_toman,
                        settings.margin_gold_upper_pct, settings.margin_gold_lower_pct,
                        instrument="gold",
                ) if current_state.gold_1g_toman > 0 else True
            
            if eurusd_rate is not None:
                trigger_fx = _breach(
                    eurusd_rate, current_state.eurusd_rate,
                        settings.margin_eurusd_upper_pct, settings.margin_eurusd_lower_pct,
                        instrument="eurusd",
                ) if current_state.eurusd_rate > 0 else True

            # Check Tether 24h_ch threshold
            if tether_24h_ch is not None:
                trigger_tether = _breach_tether_24h_ch(
                    tether_24h_ch,
                        settings.margin_tether_upper_pct,
                        settings.margin_tether_lower_pct,
                )
            else:
                trigger_tether = False

            elapsed_seconds = state_manager.get_elapsed_seconds()
            
            logger.debug("Threshold check: USD=%s, EUR=%s, Gold=%s, FX=%s, Tether=%s", 
                        trigger_usd, trigger_eur, trigger_gold, trigger_fx, trigger_tether)

            # Collect providers that were used
            used_providers = []
            if snap and snap.provider:
                used_providers.append(snap.provider)
            if eurusd_rate is not None:
                eurusd_provider = svc.get_eur_usd_provider()
                if eurusd_provider and eurusd_provider not in used_providers:
                    used_providers.append(eurusd_provider)
            # Add wallex if Tether data was successfully fetched and used
            # Only add if we actually have data (not if fetch failed)
            if tether_price_toman is not None and tether_24h_ch is not None:
                if "wallex" not in used_providers:
                    used_providers.append("wallex")

            # Build the message with % changes & elapsed time - only show items that breached thresholds
            # Note: Tether data is optional - if unavailable, omit it from the message
            try:
                text = market_lines_with_changes(
                    curr=snap,
                    curr_eur_usd=eurusd_rate,
                    prev_usd_toman=current_state.usd_toman if snap else None,
                    prev_eur_toman=current_state.eur_toman if snap else None,
                    prev_gold_1g_toman=current_state.gold_1g_toman if snap else None,
                    prev_eur_usd=current_state.eurusd_rate if eurusd_rate is not None else None,
                    elapsed_seconds=elapsed_seconds,
                    show_usd=trigger_usd,
                    show_eur=trigger_eur,
                    show_gold=trigger_gold,
                    show_eurusd=trigger_fx,
                    tether_price_toman=tether_price_toman,
                    tether_24h_ch=tether_24h_ch,
                    show_tether=trigger_tether and tether_price_toman is not None and tether_24h_ch is not None,
                    providers=used_providers if used_providers else None,
                )
            except Exception as format_error:
                # If formatting fails (e.g., due to missing Tether data), log and continue without it
                logger.warning("Failed to format message with Tether data, retrying without: %s", format_error)
                text = market_lines_with_changes(
                    curr=snap,
                    curr_eur_usd=eurusd_rate,
                    prev_usd_toman=current_state.usd_toman if snap else None,
                    prev_eur_toman=current_state.eur_toman if snap else None,
                    prev_gold_1g_toman=current_state.gold_1g_toman if snap else None,
                    prev_eur_usd=current_state.eurusd_rate if eurusd_rate is not None else None,
                    elapsed_seconds=elapsed_seconds,
                    show_usd=trigger_usd,
                    show_eur=trigger_eur,
                    show_gold=trigger_gold,
                    show_eurusd=trigger_fx,
                    tether_price_toman=None,  # Skip Tether if formatting failed
                    tether_24h_ch=None,
                    show_tether=False,
                    providers=used_providers if used_providers else None,
                )

            try:
                if (trigger_usd or trigger_eur or trigger_gold or trigger_fx or trigger_tether):
                    logger.info("Threshold breached - posting update to channel")
                    try:
                        await context.bot.send_message(
                            chat_id=settings.channel_id,
                            text=text,
                        )
                    except RetryAfter as e:
                        logger.warning("Telegram rate limit (429): retry after %s seconds", e.retry_after)
                        # Wait and retry once with exponential backoff
                        wait_time = float(e.retry_after) + 1
                        await asyncio.sleep(wait_time)
                        await context.bot.send_message(
                            chat_id=settings.channel_id,
                            text=text,
                        )
                    except TimedOut:
                        logger.warning("Telegram request timed out, will retry on next job run")
                        raise  # Re-raise to trigger outer exception handler
                    
                    # Generate and send analysis from Avalai API
                    # This is completely non-blocking - failures here never affect the main job
                    # The price post above is already successful at this point
                    try:
                        logger.info("Starting Avalai analysis generation for scheduled post")
                        avalai = _get_avalai_service()
                        if avalai:
                            logger.info("Avalai service obtained, checking client availability")
                            if avalai.client:
                                logger.info("Generating market analysis from Avalai API (scheduled post)")
                                # Use asyncio timeout to prevent hanging on slow API
                                try:
                                    analysis = await asyncio.wait_for(
                                        avalai.generate_analysis(price_message=text),
                                        timeout=30.0  # 30 second timeout for Avalai API
                                    )
                                    if analysis:
                                        logger.info("Analysis received, sending to channel (length=%d chars)", len(analysis))
                                        # Send analysis as a separate message to the channel
                                        await context.bot.send_message(
                                            chat_id=settings.channel_id,
                                            text=analysis,
                                        )
                                        logger.info("Avalai analysis sent to channel successfully")
                                    else:
                                        logger.warning("No analysis generated from Avalai API (returned None)")
                                except asyncio.TimeoutError:
                                    logger.warning("Avalai API call timed out after 30 seconds - analysis skipped")
                                except Exception as avalai_error:
                                    logger.warning("Avalai API call failed (non-blocking): %s", avalai_error, exc_info=True)
                            else:
                                logger.warning("Avalai client not initialized - API key may be missing or invalid")
                        else:
                            logger.warning("Avalai service not available (service creation failed or API key not configured)")
                    except Exception as e:
                        # Catch-all for any unexpected errors in Avalai integration
                        # Never let this affect the main job - price post was already successful
                        logger.warning("Unexpected error in Avalai analysis (non-blocking): %s", e, exc_info=True)
                        # Job continues normally - analysis is optional
                    
                    # Track the post
                    stats_tracker.record_post(providers=used_providers, is_manual=False)
                    # Only update state if we have actual data
                    if snap or eurusd_rate is not None:
                        state_manager.update_state(
                            usd_toman=snap.usd_toman if snap else current_state.usd_toman,
                            eur_toman=snap.eur_toman if snap else current_state.eur_toman,
                            gold_1g_toman=snap.gold_1g_toman if snap else current_state.gold_1g_toman,
                            eurusd_rate=eurusd_rate if eurusd_rate is not None else current_state.eurusd_rate,
                            tether_price_toman=tether_price_toman if tether_price_toman is not None else current_state.tether_price_toman,
                            tether_24h_ch=tether_24h_ch if tether_24h_ch is not None else current_state.tether_24h_ch,
                            ts=now,
                        )
                    logger.info("New baseline set and persisted")
                else:
                    logger.debug("No threshold breached - skipping post")
            except Exception as e:
                logger.error("Failed to post message to channel: %s", e)
                stats_tracker.record_error(str(e))


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
• USD: ↑{settings.margin_usd_upper_pct}% / ↓{settings.margin_usd_lower_pct}%
• EUR: ↑{settings.margin_eur_upper_pct}% / ↓{settings.margin_eur_lower_pct}%
• Gold: ↑{settings.margin_gold_upper_pct}% / ↓{settings.margin_gold_lower_pct}%
• EUR/USD: ↑{settings.margin_eurusd_upper_pct}% / ↓{settings.margin_eurusd_lower_pct}%
• Tether: ↑{settings.margin_tether_upper_pct}% / ↓{settings.margin_tether_lower_pct}%

💾 **Cache Settings**
• FastForex: {settings.fastforex_cache_minutes} min
• Navasan: {settings.navasan_cache_minutes} min
• BRS API: {settings.brsapi_cache_minutes} min
• Wallex: {settings.wallex_cache_minutes} min"""

        # Build commands list
        commands_list = """📋 **Available Commands**
• `/start` - Get current market data (Public)
• `/irr` - Get Iranian market snapshot (Public)
• `/health` - Check system health (Public)
• `/post` - Manually post to channel (Admin)
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
        
        # Format provider usage
        provider_text = ""
        if provider_usage:
            provider_items = []
            for provider, count in sorted(provider_usage.items(), key=lambda x: x[1], reverse=True):
                provider_items.append(f"• {provider}: {count}")
            provider_text = "\n".join(provider_items)
        else:
            provider_text = "• No provider usage data"
        
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
{provider_text}

🕐 Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"""
        
        await context.bot.send_message(
            chat_id=admin_user_id,
            text=message,
            parse_mode="Markdown",
        )
        logger.info("Daily summary sent to admin")
    except Exception as e:
        logger.error("Failed to send daily summary: %s", e)
