# src/xrate/adapters/telegram/bot.py
"""
Telegram Bot - Application Builder and Middlewares

This module provides bot application building utilities,
middlewares, and rate limiting integration.
"""

from __future__ import annotations

from telegram.ext import Application

from xrate.shared.rate_limiter import rate_limiter


def build_application(bot_token: str) -> Application:
    """
    Build Telegram bot application with configured middlewares.
    
    Args:
        bot_token: Telegram bot token
        
    Returns:
        Configured Application instance
    """
    return Application.builder().token(bot_token).build()

