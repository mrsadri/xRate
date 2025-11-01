# src/xrate/adapters/formatting/__init__.py
"""
Formatting Adapters - Message Formatting

This package contains message formatting adapters for Telegram output.
"""

from xrate.adapters.formatting.formatter import (
    format_irr_snapshot,
    market_lines,
    market_lines_with_changes,
)

__all__ = [
    "format_irr_snapshot",
    "market_lines",
    "market_lines_with_changes",
]

