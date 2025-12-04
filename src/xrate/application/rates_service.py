# src/xrate/application/rates_service.py
"""
Rates Service - Business Logic for Exchange Rate Operations

This module contains the core business logic for exchange rate operations.
It provides high-level services for fetching and processing market data,
including Iranian market data (USD/EUR/Gold in Toman) from crawlers and APIs.

Files that USE this module:
- xrate.adapters.telegram.handlers (uses get_irr_snapshot)
- xrate.adapters.telegram.jobs (uses get_irr_snapshot)
- tests.test_rates_service (unit tests)

Files that this module USES:
- xrate.adapters.providers.navasan (NavasanProvider for fallback Iranian market data)
- xrate.domain.models (IrrSnapshot domain model)
- xrate.application.crawler_service (get_crawler_snapshot for crawler data)
"""
from __future__ import annotations  # Enable postponed evaluation of annotations

from typing import Mapping, Optional  # Type hints for mappings and optional values

from xrate.domain.models import IrrSnapshot  # Domain model for Iranian market snapshot
from xrate.adapters.providers.navasan import NavasanProvider  # Navasan API provider for market data
from xrate.config import settings  # Application configuration and settings


def _to_int(s: str) -> int:
    """
    Convert string to integer, handling commas and decimals.
    
    Args:
        s: String to convert (e.g., '108400', '10,948,570', '123.45')
        
    Returns:
        Integer value (decimals are truncated, not rounded)
    """
    s = str(s).replace(",", "")
    return int(float(s or 0))


def get_irr_snapshot() -> Optional[IrrSnapshot]:
    """
    Fetch USD/EUR/18k Gold (IR market) from crawlers first, then fallback to Navasan API.
    
    Priority order:
    1. Crawlers (Bonbast first, then AlanChand as fallback)
    2. Navasan API (final fallback)
    
    Normalized to Toman integers.
    Returns None if all sources are unavailable or fail.
    """
    import logging
    log = logging.getLogger(__name__)
    
    # Try crawlers first (priority: crawlers > APIs)
    try:
        from xrate.application.crawler_service import get_crawler_snapshot
        crawler_snap = get_crawler_snapshot()
        if crawler_snap:
            log.info("Successfully fetched IRR snapshot from crawlers")
            return crawler_snap
    except Exception as e:
        log.warning("Crawler service failed, falling back to Navasan API: %s", e)
    
    # Final fallback to Navasan (only if API key is configured)
    try:
        if not settings.navasan_key:
            log.info("Navasan API key not configured, skipping fallback")
            return None
        
        provider = NavasanProvider()
        vals: Mapping[str, str] = provider.get_values(["usd", "eur", "18ayar"])

        # Handle NOT_FOUND from Navasan provider
        usd_val = vals.get("usd", "0")
        eur_val = vals.get("eur", "0")
        gold_val = vals.get("18ayar", "0")
        
        # Skip if any value is NOT_FOUND
        if usd_val == "NOT_FOUND" or eur_val == "NOT_FOUND" or gold_val == "NOT_FOUND":
            log.warning("Navasan returned NOT_FOUND for some keys, treating as unavailable")
            return None
        
        usd_toman = _to_int(usd_val)
        eur_toman = _to_int(eur_val)
        gold_1g_toman = _to_int(gold_val)

        # If your '18ayar' is in Rial, uncomment:
        # gold_1g_toman //= 10

        # Check if we got valid data (all zeros likely means failure)
        if usd_toman == 0 and eur_toman == 0 and gold_1g_toman == 0:
            log.warning("Navasan returned all-zero values, treating as unavailable")
            return None

        log.info("Successfully fetched IRR snapshot from Navasan (fallback)")
        return IrrSnapshot(
            usd_toman=usd_toman,
            eur_toman=eur_toman,
            gold_1g_toman=gold_1g_toman,
            provider="navasan",
        )
    except Exception as e:
        log.error("All sources failed. Crawlers and Navasan all failed. Last error: %s", e)
        return None
