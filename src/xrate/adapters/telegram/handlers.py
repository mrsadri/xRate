# src/xrate/adapters/telegram/handlers.py
"""
Telegram Handlers - Command Processing and User Interaction

This module contains all Telegram bot command handlers and message processing logic.
It handles user commands (/start, /irr, /health), admin commands (/post, /language),
and implements rate limiting, input validation, and error handling for all interactions.

Files that USE this module:
- xrate.app (build_handlers function creates handler instances)

Files that this module USES:
- xrate.application.rates_service (RatesService, get_irr_snapshot)
- xrate.adapters.formatting.formatter (all formatter functions)
- xrate.application.state_manager (state_manager for baseline data)
- xrate.shared.rate_limiter (rate limiting functionality)
- xrate.application.health (health_checker for health monitoring)
- xrate.adapters.persistence.file_store (load_last, save_last, LastSnapshot)
- xrate.adapters.persistence.admin_store (admin_store for admin user ID)
- xrate.shared.language (language management functions)
- xrate.config (settings for configuration)
"""
from __future__ import annotations

import logging
import os
from functools import partial
from datetime import datetime, timezone
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, RetryAfter, TimedOut
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from xrate.application.rates_service import RatesService, get_irr_snapshot
from xrate.adapters.formatting.formatter import (
    market_lines,
    format_irr_snapshot,
    market_lines_with_changes,
)

# Import in-memory baseline maintained by the scheduled job
from xrate.application.state_manager import state_manager
from xrate.adapters.persistence.admin_store import admin_store
from xrate.adapters.persistence.file_store import load_last, LastSnapshot
from xrate.shared.rate_limiter import rate_limiter, RATE_LIMITS
from xrate.application.health import health_checker
from xrate.shared.language import set_language, get_language, LANG_ENGLISH, LANG_FARSI
from xrate.application.stats import stats_tracker
from xrate.adapters.ai.avalai import AvalaiService

from xrate.config import settings

CHANNEL_ID = settings.channel_id
ADMIN_USERNAME = settings.admin_username

logger = logging.getLogger(__name__)


def _get_baseline():
    """
    Get the baseline market state for comparison.
    
    Returns:
        Tuple of (usd_toman, eur_toman, gold_1g_toman, eurusd_rate, timestamp) 
        or None if no baseline exists
    """
    current_state = state_manager.get_current_state()
    if current_state:
        return (current_state.usd_toman, current_state.eur_toman, 
                current_state.gold_1g_toman, current_state.eurusd_rate, current_state.ts)
    return None


# --- /health: System health check ---
async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /health command - check and report system health status.
    
    Checks all components (BRS API, FastForex, Navasan, state manager, data fetch)
    and returns a formatted health report.
    """
    # Store admin user ID if this is the admin
    if _is_admin(update):
        user_id = update.effective_user.id
        admin_store.set_admin_user_id(user_id)
    
    # Check rate limit
    if not _check_rate_limit(update, "health_check"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return
    
    try:
        health_status = health_checker.get_overall_health()
        
        if health_status["overall_healthy"]:
            status_emoji = "✅"
            status_text = "All systems healthy"
        else:
            status_emoji = "⚠️"
            status_text = "Some issues detected"
        
        message = f"{status_emoji} **System Health Check**\n\n{status_text}\n\n"
        
        for check_name, check_data in health_status["checks"].items():
            check_emoji = "✅" if check_data["healthy"] else "❌"
            message += f"{check_emoji} **{check_name.replace('_', ' ').title()}**: {check_data['message']}\n"
        
        message += f"\n🕐 Checked at: {health_status['timestamp']}"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.exception("Health check failed")
        await update.message.reply_text(f"Health check failed: {e}")


# --- /irr: Market snapshot (debug/info) ---
async def irr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /irr command - display current Iranian market snapshot.
    
    Shows USD, EUR, and 18K gold prices in Toman from BRS API or Navasan fallback.
    """
    # Store admin user ID if this is the admin
    if _is_admin(update):
        user_id = update.effective_user.id
        admin_store.set_admin_user_id(user_id)
    
    # Check rate limit
    if not _check_rate_limit(update, "user_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return
    
    try:
        snap = get_irr_snapshot()
        if snap is None:
            await update.message.reply_text("⚠️ Market data is currently unavailable.")
            return
        text = format_irr_snapshot("IRR Market Snapshot (BRS/Navasan)", snap)
        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("Failed to fetch market data")
        await update.message.reply_text(f"Failed to fetch market data: {e}")


# --- /start: 4-line market message (with deltas if baseline exists) ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, svc: RatesService) -> None:
    """
    Handle /start command - display market data message.
    
    Shows current market rates with percentage changes if baseline exists.
    Formats: USD, EUR, Gold prices, and EUR/USD rate.
    """
    # Store admin user ID if this is the admin
    if _is_admin(update):
        user_id = update.effective_user.id
        admin_store.set_admin_user_id(user_id)
    
    # Check rate limit
    if not _check_rate_limit(update, "user_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return
    
    try:
        rate = svc.eur_usd()
        snap = get_irr_snapshot()
        
        # Check if we have at least some data
        if rate is None and snap is None:
            await update.message.reply_text(
                "⚠️ All data sources are currently unavailable. Please try again later."
            )
            return
        
        # Collect providers
        used_providers = []
        if snap and snap.provider:
            used_providers.append(snap.provider)
        if rate is not None:
            eurusd_provider = svc.get_eur_usd_provider()
            if eurusd_provider and eurusd_provider not in used_providers:
                used_providers.append(eurusd_provider)
        
        baseline = _get_baseline()
        if baseline:
            prev_usd, prev_eur, prev_gold, prev_fx, prev_ts = baseline
            elapsed_seconds = int((datetime.now(timezone.utc) - prev_ts).total_seconds())
            text = market_lines_with_changes(
                curr=snap,
                curr_eur_usd=rate,
                prev_usd_toman=prev_usd if snap else None,
                prev_eur_toman=prev_eur if snap else None,
                prev_gold_1g_toman=prev_gold if snap else None,
                prev_eur_usd=prev_fx if rate is not None else None,
                elapsed_seconds=elapsed_seconds,
                providers=used_providers if used_providers else None,
            )
        else:
            text = market_lines(snap, rate, providers=used_providers if used_providers else None)

        await update.message.reply_text(text)
    except Exception:
        logger.exception("start_cmd failed")
        await update.message.reply_text("Sorry, I couldn't fetch market data right now.")


def _check_rate_limit(update: Update, limit_type: str) -> bool:
    """
    Check if user is within configured rate limits.
    
    Uses namespaced buckets to prevent rate limit conflicts between different command types:
    - public:user:123 for public user commands
    - admin:user:123 for admin commands
    - health:chat:123 for health checks (per chat to handle group spam)
    
    Args:
        update: Telegram update object
        limit_type: Type of rate limit to check (e.g., "user_command", "admin_command", "health_check")
        
    Returns:
        True if allowed, False if rate limit exceeded
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id) if update.effective_chat else user_id
    
    config = RATE_LIMITS.get(limit_type)
    
    if not config:
        return True  # No rate limit configured
    
    # Create namespaced identifier based on limit type
    # This ensures admin commands don't share buckets with public commands
    if limit_type == "admin_command":
        identifier = f"admin:user:{user_id}"
    elif limit_type == "health_check":
        # Use chat_id for health checks to prevent group spam from affecting individual users
        identifier = f"health:chat:{chat_id}"
    else:
        # Default: public user commands
        identifier = f"public:user:{user_id}"
    
    if not rate_limiter.is_allowed(identifier, config):
        logger.warning(
            "Rate limit exceeded for %s (type=%s, remaining=%s, reset_time=%s)",
            identifier,
            limit_type,
            rate_limiter.get_remaining_requests(identifier, config),
            rate_limiter.get_reset_time(identifier, config)
        )
        return False
    
    return True


def _is_admin(update: Update) -> bool:
    """
    Check if the user sending the update is an admin.
    
    Args:
        update: Telegram update object
        
    Returns:
        True if user is admin (username matches ADMIN_USERNAME), False otherwise
    """
    user = update.effective_user
    uname = (user.username or "").lstrip("@")
    return uname.lower() == (ADMIN_USERNAME or "MasihSadri").lstrip("@").lower()


async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, svc: RatesService) -> None:
    """
    Handle /post command - manually post market update to channel (admin only).
    
    Only accessible by admin users. Fetches current market data, formats message
    with percentage changes, posts to configured channel, and updates baseline state.
    """
    if not _is_admin(update):
        await update.message.reply_text("You're not allowed to run this command.")
        return
    
    # Store admin user ID for notifications
    user_id = update.effective_user.id
    admin_store.set_admin_user_id(user_id)

    # Check rate limit for admin commands
    if not _check_rate_limit(update, "admin_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return

    if not CHANNEL_ID:
        await update.message.reply_text("CHANNEL_ID is not configured.")
        logger.error("CHANNEL_ID missing; cannot post to channel.")
        return

    # Fetch data (these methods now return None on failure instead of raising)
    rate = svc.eur_usd()
    snap = get_irr_snapshot()
    
    # Fetch Tether data from Wallex API
    from xrate.adapters.providers.wallex import WallexProvider
    tether_price_toman: Optional[int] = None
    tether_24h_ch: Optional[float] = None
    try:
        wallex_provider = WallexProvider()
        tether_data = wallex_provider.get_tether_data()
        if tether_data:
            tether_price_toman = int(tether_data["price"])
            tether_24h_ch = float(tether_data["24h_ch"])
    except Exception as e:
        logger.warning("Failed to fetch Tether data from Wallex in /post: %s", e)
    
    # Check if we have at least some data
    if rate is None and snap is None:
        await update.message.reply_text(
            "⚠️ All data sources are currently unavailable. Cannot post to channel."
        )
        return

    # Collect providers
    used_providers = []
    if snap and snap.provider:
        used_providers.append(snap.provider)
    if rate is not None:
        eurusd_provider = svc.get_eur_usd_provider()
        if eurusd_provider and eurusd_provider not in used_providers:
            used_providers.append(eurusd_provider)
    # Add wallex if Tether data was fetched
    if tether_price_toman is not None:
        if "wallex" not in used_providers:
            used_providers.append("wallex")
    
    # Get current state for showing changes
    current_state = state_manager.get_current_state()
    baseline = _get_baseline()
    
    # For manual post (/post), always show all available items regardless of thresholds
    # This gives admin full control to post everything when needed
    trigger_usd = True if snap else False
    trigger_eur = True if snap else False
    trigger_gold = True if snap else False
    trigger_fx = True if rate is not None else False
    trigger_tether = True if tether_24h_ch is not None else False
    
    # Format the message (with changes if baseline exists)
    if baseline and current_state:
        prev_usd, prev_eur, prev_gold, prev_fx, prev_ts = baseline
        elapsed_seconds = int((datetime.now(timezone.utc) - prev_ts).total_seconds())
        text = market_lines_with_changes(
            curr=snap,
            curr_eur_usd=rate,
            prev_usd_toman=prev_usd if snap else None,
            prev_eur_toman=prev_eur if snap else None,
            prev_gold_1g_toman=prev_gold if snap else None,
            prev_eur_usd=prev_fx if rate is not None else None,
            elapsed_seconds=elapsed_seconds,
            show_usd=trigger_usd,
            show_eur=trigger_eur,
            show_gold=trigger_gold,
            show_eurusd=trigger_fx,
            tether_price_toman=tether_price_toman,
            tether_24h_ch=tether_24h_ch,
            show_tether=trigger_tether,
            providers=used_providers if used_providers else None,
        )
    else:
        text = market_lines(snap, rate, providers=used_providers if used_providers else None)

    try:
        # Post to channel
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        logger.info("Price message posted to channel via /post command")

        # Generate and send analysis from Avalai API
        try:
            avalai = AvalaiService()
            if avalai and avalai.client:
                logger.info("Generating market analysis from Avalai API (manual /post)")
                analysis = await avalai.generate_analysis(price_message=text)
                if analysis:
                    logger.info("Avalai analysis generated successfully, sending to channel")
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=analysis)
                    logger.info("Avalai analysis sent to channel successfully")
                else:
                    logger.warning("Avalai API returned no analysis (None)")
            else:
                logger.debug("Avalai service not available - API key not configured or client not initialized")
        except Exception as e:
            logger.exception("Failed to generate or send Avalai analysis in /post command: %s", e)
            # Don't fail the main post if analysis fails

        # Update state using the centralized state manager (only if we have data)
        now = datetime.now(timezone.utc)
        if snap or rate is not None:
            state_manager.update_state(
                usd_toman=snap.usd_toman if snap else 0,
                eur_toman=snap.eur_toman if snap else 0,
                gold_1g_toman=snap.gold_1g_toman if snap else 0,
                eurusd_rate=rate if rate is not None else 0.0,
                tether_price_toman=tether_price_toman if tether_price_toman is not None else 0,
                tether_24h_ch=tether_24h_ch if tether_24h_ch is not None else 0.0,
                ts=now,
            )

        # Track the post
        stats_tracker.record_post(providers=used_providers, is_manual=True)
        
        # Ack
        await update.message.reply_text("Posted to channel ✅")
    except Exception as e:
        logger.exception("post_cmd failed during posting to channel")
        stats_tracker.record_error(str(e))
        # Show the user what was supposed to be posted
        await update.message.reply_text(
            f"⚠️ Failed to post to channel: {e}\n\n"
            f"Here's what would have been posted:\n\n{text}"
        )


# --- Fallback: reply with market message ---
async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE, svc: RatesService) -> None:
    """
    Handle any text message (non-command).
    
    Displays current market data with percentage changes if baseline exists.
    """
    # Store admin user ID if this is the admin
    if _is_admin(update):
        user_id = update.effective_user.id
        admin_store.set_admin_user_id(user_id)
    
    # Check rate limit
    if not _check_rate_limit(update, "user_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return
    
    try:
        rate = svc.eur_usd()
        snap = get_irr_snapshot()
        
        # Check if we have at least some data
        if rate is None and snap is None:
            await update.message.reply_text(
                "⚠️ All data sources are currently unavailable. Please try again later."
            )
            return
        
        # Collect providers
        used_providers = []
        if snap and snap.provider:
            used_providers.append(snap.provider)
        if rate is not None:
            eurusd_provider = svc.get_eur_usd_provider()
            if eurusd_provider and eurusd_provider not in used_providers:
                used_providers.append(eurusd_provider)
        
        baseline = _get_baseline()
        if baseline:
            prev_usd, prev_eur, prev_gold, prev_fx, prev_ts = baseline
            elapsed_seconds = int((datetime.now(timezone.utc) - prev_ts).total_seconds())
            text = market_lines_with_changes(
                curr=snap,
                curr_eur_usd=rate,
                prev_usd_toman=prev_usd if snap else None,
                prev_eur_toman=prev_eur if snap else None,
                prev_gold_1g_toman=prev_gold if snap else None,
                prev_eur_usd=prev_fx if rate is not None else None,
                elapsed_seconds=elapsed_seconds,
                providers=used_providers if used_providers else None,
            )
        else:
            text = market_lines(snap, rate, providers=used_providers if used_providers else None)

        await update.message.reply_text(text)
    except Exception:
        logger.exception("any_message failed")
        await update.message.reply_text("Sorry, I couldn't fetch market data right now.")


# --- /language: Language selection (admin only) ---
async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /language command - show language selection buttons (admin only).
    
    Displays inline keyboard with English and Farsi options for admin users.
    """
    if not _is_admin(update):
        await update.message.reply_text("You're not allowed to run this command.")
        return
    
    # Store admin user ID for notifications
    user_id = update.effective_user.id
    admin_store.set_admin_user_id(user_id)
    
    # Check rate limit
    if not _check_rate_limit(update, "admin_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("فارسی", callback_data="lang_fa"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_lang = get_language()
    lang_text = "English" if current_lang == LANG_ENGLISH else "فارسی"
    
    await update.message.reply_text(
        f"Select language / انتخاب زبان\n\nCurrent language / زبان فعلی: {lang_text}",
        reply_markup=reply_markup
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle language selection callback from inline keyboard.
    
    Only admin users can change language.
    """
    query = update.callback_query
    await query.answer()
    
    if not _is_admin(update):
        await query.edit_message_text("You're not allowed to change language.")
        return
    
    if query.data == "lang_en":
        success = set_language(LANG_ENGLISH)
        if success:
            # Verify the language was actually set
            current = get_language()
            if current == LANG_ENGLISH:
                await query.edit_message_text("✅ Language changed to English")
            else:
                logger.error("Language change verification failed: expected %s but got %s", LANG_ENGLISH, current)
                await query.edit_message_text(f"⚠️ Language change may have failed (current: {current})")
        else:
            await query.edit_message_text("❌ Failed to change language")
    elif query.data == "lang_fa":
        success = set_language(LANG_FARSI)
        if success:
            # Verify the language was actually set
            current = get_language()
            logger.info("Language change: set to %s, verified as %s", LANG_FARSI, current)
            if current == LANG_FARSI:
                await query.edit_message_text("✅ زبان به فارسی تغییر کرد\n\nلطفاً دستوری مانند /start را امتحان کنید تا تغییر را ببینید.")
            else:
                logger.error("Language change verification failed: expected %s but got %s", LANG_FARSI, current)
                await query.edit_message_text(f"⚠️ تغییر زبان ممکن است ناموفق بوده باشد (فعلی: {current})")
        else:
            await query.edit_message_text("❌ تغییر زبان ناموفق بود")
    else:
        await query.edit_message_text("Invalid language selection")


def build_handlers(svc: RatesService):
    """
    Build and return list of Telegram bot handlers.
    
    Args:
        svc: RatesService instance to inject into handlers
        
    Returns:
        List of handler instances for registration with bot
    """
    return [
        CommandHandler("start", partial(start_cmd, svc=svc)),
        CommandHandler("irr", irr),
        CommandHandler("health", health),
        CommandHandler("language", language_cmd),
        CommandHandler("post", partial(post_cmd, svc=svc)),  # Admin command to manually post
        CallbackQueryHandler(language_callback, pattern="^lang_"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, partial(any_message, svc=svc)),
    ]
