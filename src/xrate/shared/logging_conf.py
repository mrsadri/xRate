# src/xrate/shared/logging_conf.py
"""
Logging Configuration - Logging Setup and Configuration

This module provides centralized logging configuration for the entire application.
It sets up structured logging with consistent formatting, log levels, and output
handlers to ensure proper logging throughout all modules.

Files that USE this module:
- xrate.app (setup_logging function for logging initialization)

Files that this module USES:
- None (pure configuration module)
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union
from logging.handlers import RotatingFileHandler


def setup_logging(
    level=logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    log_dir: Optional[Union[str, Path]] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure application-wide logging settings.
    
    Sets up structured logging with consistent formatting. Can output to stdout,
    file, or both. Supports log rotation for file logging.
    
    Args:
        level: Logging level (default: logging.INFO)
              Options: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR
        log_file: Optional path to log file (enables file logging)
        log_dir: Optional directory for log files (defaults to ./logs)
        max_bytes: Maximum size per log file before rotation (default: 10MB)
        backup_count: Number of backup log files to keep (default: 5)
    """
    # Default log format
    log_format = "%(asctime)s %(levelname)s %(name)s :: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    handlers = []
    
    # Determine if we should log to stdout
    # Only log to stdout if not running under systemd/supervisor (which capture output)
    # or if explicitly requested via environment variable
    log_to_stdout = os.environ.get("XRATE_LOG_STDOUT", "true").lower() == "true"
    
    if log_to_stdout:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(stdout_handler)
    
    # File logging (if log_file or log_dir is specified)
    if log_file or log_dir:
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir / "xrate.log"
        else:
            log_file_path = Path(log_file)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)
    
    # If no handlers specified, default to stdout
    if not handlers:
        handlers = [logging.StreamHandler(sys.stdout)]
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )
    
    # Log where logging is configured
    logger = logging.getLogger(__name__)
    if log_file or log_dir:
        logger.info("Logging configured: file=%s, level=%s", log_file_path, level)
    else:
        logger.info("Logging configured: stdout, level=%s", level)
