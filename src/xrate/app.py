# src/xrate/app.py
"""
Application Entry Point - Bot Initialization and Startup

This module serves as the composition root for the XRate Telegram bot.
It wires all dependencies and starts the bot application.

Files that USE this module:
- scripts/run.sh (executes this script to start the bot)
- python -m xrate (module entry point)

Files that this module USES:
- xrate.shared.logging_conf (setup_logging for logging configuration)
- xrate.config (settings for configuration management)
- xrate.adapters.providers.brsapi (BRSAPIProvider for primary market data)
- xrate.adapters.providers.fastforex (FastForexProvider for EUR→USD fallback)
- xrate.application.rates_service (RatesService for business logic)
- xrate.adapters.telegram.handlers (build_handlers for command handlers)
- xrate.adapters.telegram.jobs (post_rate_job for scheduled tasks)
"""

from __future__ import annotations

import logging
import os
import sys
import atexit
from datetime import timedelta, time
from functools import partial
from pathlib import Path

from telegram.ext import Application
from telegram.error import TimedOut, NetworkError, Conflict

from xrate.shared.logging_conf import setup_logging
from xrate.adapters.providers.fastforex import FastForexProvider
from xrate.adapters.providers.brsapi import BRSAPIProvider
from xrate.application.rates_service import RatesService, ProviderChain
from xrate.adapters.telegram.handlers import build_handlers
from xrate.adapters.telegram.jobs import post_rate_job, startup_notification, daily_summary_job


# PID file path for preventing multiple instances
# Can be overridden via XRATE_PID_FILE environment variable
def _get_pid_file() -> Path:
    """Get PID file path from environment or default location."""
    pid_file = os.environ.get("XRATE_PID_FILE")
    if pid_file:
        return Path(pid_file)
    # Default: use data directory from settings or current directory
    # Lazy import to avoid circular dependency
    try:
        from xrate.config import settings
        data_dir = settings.last_state_file.parent
    except Exception:
        # Fallback if settings not loaded yet
        data_dir = Path("./data")
    return data_dir / "bot.pid"


def _check_existing_instance() -> None:
    """
    Check if another bot instance is already running.
    
    Raises RuntimeError if PID file exists and process is still running.
    """
    pid_file = _get_pid_file()
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            
            # Check if process is still running
            try:
                os.kill(old_pid, 0)  # Signal 0 doesn't kill, just checks if process exists
                raise RuntimeError(
                    f"Another bot instance is already running (PID: {old_pid}).\n"
                    f"Please stop it first with: kill {old_pid}\n"
                    f"Or kill all instances with: pkill -f 'python.*xrate'"
                )
            except ProcessLookupError:
                # Process doesn't exist, stale PID file - remove it
                pid_file.unlink()
        except (ValueError, IOError):
            # Invalid PID file, remove it
            pid_file.unlink()


def _create_pid_file() -> None:
    """Create PID file with current process ID."""
    pid_file = _get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


def _remove_pid_file() -> None:
    """Remove PID file on exit."""
    pid_file = _get_pid_file()
    if pid_file.exists():
        try:
            pid_file.unlink()
        except Exception:
            pass


def main() -> None:
    """
    Initialize and start the Telegram bot application.
    
    This function:
    1. Sets up logging and validates configuration
    2. Creates Telegram application instance
    3. Initializes provider chain (BRS primary, FastForex fallback)
    4. Registers command and message handlers
    5. Schedules periodic job for market updates
    6. Starts the bot polling loop
    """
    # Logging + config
    # Import settings here to avoid circular dependency
    from xrate.config import settings
    
    # Setup logging with file support if configured
    setup_logging(
        level=logging.INFO,
        log_file=settings.log_file,
        log_dir=settings.log_dir,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )
    logger = logging.getLogger(__name__)
    
    # Log working directory for debugging
    logger.info("Working directory: %s", os.getcwd())
    logger.info("PID file location: %s", _get_pid_file())

    # Check for existing bot instance (prevent multiple instances)
    try:
        _check_existing_instance()
        _create_pid_file()
        atexit.register(_remove_pid_file)
        logger.info("Bot instance lock acquired (PID: %d)", os.getpid())
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)

    # Validate settings (Pydantic validates automatically, but check required fields)
    # Note: settings is imported in setup_logging above
    from xrate.config import settings
    
    if not settings.bot_token:
        _remove_pid_file()
        raise RuntimeError("BOT_TOKEN missing")

    # Telegram app
    # poll_interval controls how often we check for updates (default ~10 seconds)
    # This is separate from scheduled jobs - it only affects command responsiveness
    # Lower values = more responsive but more API calls
    # Telegram allows up to 30 req/sec, so even 1 second would be safe
    app = Application.builder().token(settings.bot_token).build()

    # Dependency injection: BRS API as primary, FastForex as fallback for EUR→USD
    brs_provider = BRSAPIProvider()
    fastforex_provider = FastForexProvider()
    provider_chain = ProviderChain(primary=brs_provider, fallback=fastforex_provider)
    svc = RatesService(provider=provider_chain)

    # Handlers
    for h in build_handlers(svc):
        app.add_handler(h)

    # Scheduled job (interval from .env)
    app.job_queue.run_repeating(
        callback=partial(post_rate_job, svc=svc),
        interval=timedelta(minutes=settings.post_interval_minutes),
        first=0,  # start immediately at boot
        name="eur_usd_poster",
    )
    
    # Daily summary job at 9 PM (21:00) local time (timezone-aware)
    # Use UTC timezone for consistency (or configure via settings if needed)
    from zoneinfo import ZoneInfo
    # Default to UTC, but can be configured to use local timezone (e.g., Europe/Berlin)
    daily_summary_tz = ZoneInfo("UTC")  # Can be made configurable via settings
    daily_summary_time = time(21, 0, 0, tzinfo=daily_summary_tz)
    app.job_queue.run_daily(
        callback=daily_summary_job,
        time=daily_summary_time,  # 9 PM timezone-aware
        name="daily_summary",
    )
    
    # Startup notification (send after bot is ready - run once after 5 seconds)
    app.job_queue.run_once(
        callback=startup_notification,
        when=5,  # 5 seconds after startup
        name="startup_notification",
    )

    logger.info(
        "Starting bot polling… post interval=%d minutes",
        settings.post_interval_minutes,
    )
    
    # Run polling with error handling
    # Note: app.run_polling() will call app.initialize() internally,
    # which calls bot.get_me() to verify the token - this can timeout on network issues
    try:
        app.run_polling(
            close_loop=False,
            stop_signals=None,  # Don't stop on SIGINT/SIGTERM (let supervisor handle it)
            allowed_updates=None,
            drop_pending_updates=False,
        )
    except Conflict as e:
        logger.error(
            "Telegram Conflict error: %s (type: %s)",
            e,
            type(e).__name__,
            exc_info=True,
        )
        logger.error(
            "This means another bot instance is already polling for updates.\n"
            "Telegram only allows ONE bot instance to poll at a time.\n"
            "To fix this:\n"
            "1) Kill all running bot instances: pkill -f 'python.*xrate'\n"
            "2) Or kill specific PID: kill <PID>\n"
            "3) Then restart the bot"
        )
        _remove_pid_file()
        raise
    except (TimedOut, NetworkError) as e:
        logger.error(
            "Network error during bot operation (timeout connecting to Telegram API): %s (type: %s)",
            e,
            type(e).__name__,
            exc_info=True,
        )
        logger.warning(
            "This could be due to: "
            "1) Network connectivity issues to api.telegram.org "
            "2) Telegram API temporary unavailability "
            "3) Firewall/proxy blocking connections"
        )
        logger.info("Bot will attempt to reconnect on next restart (via supervisor/restart script)")
        _remove_pid_file()
        raise
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
        _remove_pid_file()
        raise
    except Exception as e:
        logger.exception("Unexpected error during bot operation: %s (type: %s)", e, type(e).__name__)
        _remove_pid_file()
        raise


if __name__ == "__main__":
    main()

