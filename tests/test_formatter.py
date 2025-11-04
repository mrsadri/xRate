# tests/test_formatter.py
"""
Formatter Tests - Unit Tests for Message Formatting Functions

This module contains unit tests for all message formatting functions,
including market data display, percentage calculations, elapsed time
formatting, and various message layouts for different bot commands.

Files that USE this module:
- pytest (test runner executes these tests)

Files that this module USES:
- xrate.adapters.formatting.formatter (all formatter functions for testing)
- xrate.domain.models (IrrSnapshot for test data)
- pytest (testing framework)
"""
import pytest  # Testing framework for writing and running tests

from datetime import datetime, timezone  # Date/time utilities for test data

from xrate.adapters.formatting.formatter import (
    format_irr_snapshot,  # Format IRR snapshot with title
    eur_usd,  # Format EUR/USD exchange rate
    market_lines,  # Format market data lines
    market_lines_with_changes,  # Format market data with percentage changes
    _fmt_pct,  # Format percentage change
    _fmt_elapsed  # Format elapsed time
)
from xrate.domain.models import IrrSnapshot  # Domain model for test data


class TestFormatIrrSnapshot:
    def test_format_irr_snapshot(self):
        snap = IrrSnapshot(
            usd_toman=108400,
            eur_toman=126000,
            gold_1g_toman=10812360
        )
        
        result = format_irr_snapshot("Test Title", snap)
        
        expected_lines = [
            "Test Title",
            "— USD: 108400",
            "— EUR: 126000", 
            "— 18k Gold (1g): 10812360"
        ]
        assert result == "\n".join(expected_lines)


class TestEurUsdFormatter:
    def test_eur_usd_basic(self):
        result = eur_usd(1.1234)
        assert result == "💶 1 Euro = $1.1234 USD"

    def test_eur_usd_with_custom_decimals(self):
        result = eur_usd(1.123456, decimals=2)
        assert result == "💶 1 Euro = $1.12 USD"

    def test_eur_usd_with_time(self):
        result = eur_usd(1.1234, with_time=True)
        assert "💶 1 Euro = $1.1234 USD" in result
        assert "⏱️" in result
        assert "UTC" in result


class TestMarketLines:
    def test_market_lines(self):
        snap = IrrSnapshot(
            usd_toman=108400,
            eur_toman=126000,
            gold_1g_toman=10812360
        )
        
        result = market_lines(snap, 1.1234)
        
        assert "(USD 💵) $1   = 108.4 KToman" in result
        assert "(Euro 💶) €1  = 126.0 KToman" in result
        assert "(Gold 🏆) 1gr = 0.011 MToman" in result
        assert "(Euro 💶) €1  = $1.1234 (USD 💵)" in result


class TestMarketLinesWithChanges:
    def test_market_lines_with_changes(self):
        curr = IrrSnapshot(
            usd_toman=110000,  # Increased from 108400
            eur_toman=125000,  # Decreased from 126000
            gold_1g_toman=10812360  # Same
        )
        
        result = market_lines_with_changes(
            curr=curr,
            curr_eur_usd=1.1500,
            prev_usd_toman=108400,
            prev_eur_toman=126000,
            prev_gold_1g_toman=10812360,
            prev_eur_usd=1.1200,
            elapsed_seconds=3600  # 1 hour
        )
        
        assert "(USD 💵) $1   = 110.0 KToman" in result
        assert "(Euro 💶) €1  = 125.0 KToman" in result
        assert "(Gold 🏆) 1gr = 0.011 MToman" in result
        assert "(Euro 💶) €1  = $1.1500 (USD 💵)" in result
        assert "Time spent from previous announcement: 1h:00min" in result


class TestUtilityFunctions:
    def test_fmt_pct_increase(self):
        result = _fmt_pct(110, 100)
        assert "10.0% 📈" in result

    def test_fmt_pct_decrease(self):
        result = _fmt_pct(90, 100)
        assert "10.0% 📉" in result

    def test_fmt_pct_no_change(self):
        result = _fmt_pct(100, 100)
        assert "0.0% ⏸" in result

    def test_fmt_pct_zero_prev(self):
        result = _fmt_pct(100, 0)
        assert result == "—"

    def test_fmt_elapsed_hours_minutes(self):
        assert _fmt_elapsed(3661) == "1h:01min"  # 1 hour 1 minute
        assert _fmt_elapsed(7200) == "2h:00min"  # 2 hours exactly

    def test_fmt_elapsed_minutes_only(self):
        assert _fmt_elapsed(300) == "5min"  # 5 minutes
        assert _fmt_elapsed(60) == "1min"   # 1 minute

    def test_fmt_elapsed_negative(self):
        assert _fmt_elapsed(-100) == "0min"  # Should clamp to 0
