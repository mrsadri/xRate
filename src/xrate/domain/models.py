# src/xrate/domain/models.py
"""
Domain Models - Pure Business Objects

This module contains domain models representing core business concepts:
- Market data snapshots
- Exchange rates
- Provider attribution
- State changes

Files that USE this module:
- xrate.application.* (all services use domain models)
- xrate.adapters.* (adapters create and use domain models)
- tests.* (tests use domain models for test data)

Files that this module USES:
- None (pure domain layer, no external dependencies)
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

from dataclasses import dataclass  # Decorator for creating data classes
from datetime import datetime  # Date/time utilities for timestamps
from typing import Optional  # Type hints for optional values


@dataclass(frozen=True)
class Rate:
    """Represents an exchange rate value."""
    value: float
    timestamp: datetime


@dataclass(frozen=True)
class IrrSnapshot:
    """
    Iranian market snapshot (USD, EUR, Gold in Toman).
    
    Attributes:
        usd_toman: USD price in Toman (integer)
        eur_toman: EUR price in Toman (integer)
        gold_1g_toman: 18K gold price per gram in Toman (integer)
        provider: Name of the provider that provided this data
    """
    usd_toman: int
    eur_toman: int
    gold_1g_toman: int
    provider: Optional[str] = None


@dataclass(frozen=True)
class MarketState:
    """
    Complete market state at a point in time.
    
    Attributes:
        usd_toman: USD price in Toman
        eur_toman: EUR price in Toman
        gold_1g_toman: 18K gold price per gram in Toman
        eurusd_rate: EUR/USD exchange rate (USD per 1 EUR)
        tether_price_toman: USDT price in Toman
        tether_24h_ch: 24-hour change percentage from Wallex API
        ts: Timestamp of this state
    """
    usd_toman: int
    eur_toman: int
    gold_1g_toman: int
    eurusd_rate: float
    tether_price_toman: int = 0
    tether_24h_ch: float = 0.0
    ts: Optional[datetime] = None


@dataclass(frozen=True)
class Change:
    """
    Represents a change from previous value.
    
    Attributes:
        current: Current value
        previous: Previous value
        percentage: Percentage change
        direction: "up", "down", or "none"
    """
    current: float
    previous: float
    percentage: float
    direction: str  # "up", "down", "none"


@dataclass(frozen=True)
class ProviderAttribution:
    """
    Tracks which providers contributed to a data snapshot.
    
    Attributes:
        providers: List of provider names that contributed data
        timestamp: When this attribution was created
    """
    providers: list[str]
    timestamp: datetime

