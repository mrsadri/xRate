# src/xrate/adapters/telegram/__init__.py
"""
Telegram Adapters - Bot Interface

This package contains Telegram bot adapters:
- Bot application builder
- Command handlers
- Scheduled jobs
"""

from xrate.adapters.telegram.handlers import build_handlers
from xrate.adapters.telegram.jobs import (
    daily_summary_job,
    post_rate_job,
    startup_notification,
)

__all__ = [
    "build_handlers",
    "post_rate_job",
    "startup_notification",
    "daily_summary_job",
]

