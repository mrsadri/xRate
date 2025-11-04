# src/xrate/adapters/telegram/handlers.py
"""
Telegram Handlers - Command Processing and User Interaction

This module contains all Telegram bot command handlers and message processing logic.
It handles user commands (/start, /irr, /health), admin commands (/post, /language),
and implements rate limiting, input validation, and error handling for all interactions.

Files that USE this module:
- xrate.app (build_handlers function creates handler instances)

Files that this module USES:
- xrate.application.rates_service (get_irr_snapshot)
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

from xrate.application.rates_service import get_irr_snapshot
from xrate.adapters.formatting.formatter import (
    format_persian_market_update,
    format_persian_daily_report,
    format_irr_snapshot,
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


# --- /health: System health check (admin only) ---
async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /health command - check and report system health status (admin only).
    
    Checks all components (crawlers, Navasan, Wallex, Avalai wallet, state manager, data fetch)
    and returns a formatted health report.
    """
    # Admin-only: check if user is admin
    if not _is_admin(update):
        await update.message.reply_text("⚠️ این دستور فقط برای ادمین در دسترس است.")
        return
    
    # Store admin user ID
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
        
        # Display checks with special formatting for Avalai wallet
        for check_name, check_data in health_status["checks"].items():
            check_emoji = "✅" if check_data["healthy"] else "❌"
            # Format check name for display
            display_name = check_name.replace('_', ' ').title()
            # Special formatting for Avalai wallet to show credit prominently
            if check_name == "avalai_wallet" and check_data.get("details", {}).get("credit") is not None:
                credit = check_data["details"]["credit"]
                message += f"{check_emoji} **{display_name}**: 💰 {credit}\n"
            else:
                message += f"{check_emoji} **{display_name}**: {check_data['message']}\n"
        
        message += f"\n🕐 Checked at: {health_status['timestamp']}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Health check failed")
        await update.message.reply_text(f"Health check failed: {e}")


# --- /irr: Market snapshot (debug/info) ---
async def irr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /irr command - display current Iranian market snapshot (admin only).
    
    Shows USD, EUR, and 18K gold prices in Toman from crawlers or Navasan fallback.
    """
    # Admin-only: check if user is admin
    if not _is_admin(update):
        await update.message.reply_text("⚠️ این دستور فقط برای ادمین در دسترس است.")
        return
    
    # Store admin user ID if this is the admin
    user_id = update.effective_user.id
    admin_store.set_admin_user_id(user_id)
    
    # Check rate limit
    if not _check_rate_limit(update, "admin_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return
    
    try:
        snap = get_irr_snapshot()
        if snap is None:
            await update.message.reply_text("⚠️ داده‌های بازار در حال حاضر در دسترس نیست.")
            return
        elapsed_seconds = state_manager.get_elapsed_seconds()
        text = format_persian_daily_report(snap, elapsed_seconds)
        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("Failed to fetch market data")
        await update.message.reply_text(f"خطا در دریافت داده‌های بازار: {e}")


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


async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /post command - manually post market update to main channel (admin only).
    
    Only accessible by admin users. Posts to main channel (CHANNEL_ID).
    """
    if not _is_admin(update):
        await update.message.reply_text("⚠️ این دستور فقط برای ادمین در دسترس است.")
        return
    
    # Store admin user ID for notifications
    user_id = update.effective_user.id
    admin_store.set_admin_user_id(user_id)

    # Check rate limit for admin commands
    if not _check_rate_limit(update, "admin_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return

    if not CHANNEL_ID:
        await update.message.reply_text("⚠️ CHANNEL_ID پیکربندی نشده است.")
        logger.error("CHANNEL_ID missing; cannot post to channel.")
        return

    # Fetch data
    snap = get_irr_snapshot()
    
    if snap is None:
        await update.message.reply_text("⚠️ داده‌های بازار در دسترس نیست. امکان ارسال به کانال وجود ندارد.")
        return

    try:
        # Get current state for comparison
        current_state = state_manager.get_current_state()
        elapsed_seconds = state_manager.get_elapsed_seconds() if current_state else 0
        
        # Use Persian format
        if current_state:
            text = format_persian_market_update(
                curr=snap,
                prev_usd_toman=current_state.usd_toman,
                prev_eur_toman=current_state.eur_toman,
                prev_gold_1g_toman=current_state.gold_1g_toman,
                elapsed_seconds=elapsed_seconds,
            )
        else:
            text = format_persian_daily_report(snap, elapsed_seconds)
        
        # Post to main channel
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
        )
        
        # Update state
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        state_manager.update_state(
            usd_toman=snap.usd_toman,
            eur_toman=snap.eur_toman,
            gold_1g_toman=snap.gold_1g_toman,
            eurusd_rate=0.0,
            tether_price_toman=0,
            tether_24h_ch=0.0,
            ts=now,
        )
        
        await update.message.reply_text("✅ پیام با موفقیت به کانال اصلی ارسال شد.")
        logger.info("Manual post to main channel by admin")
    except Exception as e:
        logger.error("Failed to post to main channel: %s", e, exc_info=True)
        await update.message.reply_text(f"❌ خطا در ارسال به کانال: {str(e)}")


async def posttest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /posttest command - manually post market update to test channel (admin only).
    
    Only accessible by admin users. Posts to test channel (TEST_CHANNEL_ID).
    """
    if not _is_admin(update):
        await update.message.reply_text("⚠️ این دستور فقط برای ادمین در دسترس است.")
        return
    
    # Store admin user ID for notifications
    user_id = update.effective_user.id
    admin_store.set_admin_user_id(user_id)

    # Check rate limit for admin commands
    if not _check_rate_limit(update, "admin_command"):
        await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
        return

    test_channel_id = settings.test_channel_id
    if not test_channel_id:
        await update.message.reply_text("⚠️ TEST_CHANNEL_ID پیکربندی نشده است.")
        logger.error("TEST_CHANNEL_ID missing; cannot post to test channel.")
        return

    # Fetch data
    snap = get_irr_snapshot()
    
    if snap is None:
        await update.message.reply_text("⚠️ داده‌های بازار در دسترس نیست. امکان ارسال به کانال تست وجود ندارد.")
        return

    try:
        # Get current state for comparison
        current_state = state_manager.get_current_state()
        elapsed_seconds = state_manager.get_elapsed_seconds() if current_state else 0
        
        # Use Persian format
        if current_state:
            text = format_persian_market_update(
                curr=snap,
                prev_usd_toman=current_state.usd_toman,
                prev_eur_toman=current_state.eur_toman,
                prev_gold_1g_toman=current_state.gold_1g_toman,
                elapsed_seconds=elapsed_seconds,
            )
        else:
            text = format_persian_daily_report(snap, elapsed_seconds)
        
        # Post to test channel
        await context.bot.send_message(
            chat_id=test_channel_id,
            text=text,
        )
        
        await update.message.reply_text("✅ پیام با موفقیت به کانال تست ارسال شد.")
        logger.info("Manual post to test channel by admin")
    except Exception as e:
        logger.error("Failed to post to test channel: %s", e, exc_info=True)
        await update.message.reply_text(f"❌ خطا در ارسال به کانال تست: {str(e)}")


# --- Fallback: reply with market message ---
async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle any text message (non-command).
    
    For admin: Shows market data
    For non-admin: Stores feedback for daily report
    """
    user = update.effective_user
    username = user.username or "Unknown"
    user_id = user.id
    
    # If admin, show market data
    if _is_admin(update):
        admin_store.set_admin_user_id(user_id)
        
        # Check rate limit
        if not _check_rate_limit(update, "admin_command"):
            await update.message.reply_text("⏰ Rate limit exceeded. Please try again later.")
            return
        
        try:
            snap = get_irr_snapshot()
            if snap is None:
                await update.message.reply_text("⚠️ داده‌های بازار در حال حاضر در دسترس نیست.")
                return
            
            elapsed_seconds = state_manager.get_elapsed_seconds()
            text = format_persian_daily_report(snap, elapsed_seconds)
            await update.message.reply_text(text)
        except Exception:
            logger.exception("any_message failed for admin")
            await update.message.reply_text("متأسفانه در حال حاضر نمی‌توانم داده‌های بازار را دریافت کنم.")
    else:
        # Non-admin: store feedback
        from datetime import datetime, timezone
        from xrate.application.stats import stats_tracker
        
        message_text = update.message.text or ""
        timestamp = datetime.now(timezone.utc)
        
        # Store feedback (will be included in daily report)
        stats_tracker.record_feedback(
            user_id=user_id,
            username=username,
            message=message_text,
            timestamp=timestamp,
        )
        
        await update.message.reply_text(
            "✅ پیام شما دریافت شد و در گزارش روزانه به ادمین ارسال خواهد شد.\n\n"
            "Thank you for your feedback! Your message will be included in the daily report to admin."
        )
        logger.info("Feedback stored from user %s (@%s): %s", user_id, username, message_text[:50])


# --- /language: Language selection (admin only) ---
async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /language command - show language selection buttons (admin only).
    
    Displays inline keyboard with English and Farsi options for admin users.
    """
    # Admin-only: check if user is admin
    if not _is_admin(update):
        await update.message.reply_text("⚠️ این دستور فقط برای ادمین در دسترس است.")
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
        await query.edit_message_text("⚠️ این دستور فقط برای ادمین در دسترس است.")
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


def build_handlers():
    """
    Build and return list of Telegram bot handlers.
    
    Returns:
        List of handler instances for registration with bot
    """
    return [
        CommandHandler("irr", irr),  # Admin only - shows market snapshot
        CommandHandler("health", health),  # Admin only - health check
        CommandHandler("language", language_cmd),  # Admin only - change language
        CommandHandler("post", post_cmd),  # Admin only - post to main channel
        CommandHandler("posttest", posttest_cmd),  # Admin only - post to test channel
        CallbackQueryHandler(language_callback, pattern="^lang_"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, any_message),  # Admin shows data, others store feedback
    ]
