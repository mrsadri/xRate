# src/xrate/application/rates_service.py
"""
Rates Service - Business Logic for Exchange Rate Operations

This module contains the core business logic for exchange rate operations.
It provides high-level services for fetching and processing market data,
including EUR→USD rates and Iranian market data (USD/EUR/Gold in Toman).

Files that USE this module:
- xrate.adapters.telegram.handlers (uses RatesService and get_irr_snapshot)
- xrate.adapters.telegram.jobs (uses RatesService and get_irr_snapshot)
- tests.test_rates_service (unit tests)

Files that this module USES:
- xrate.adapters.providers.brsapi (BRSAPIProvider for primary Iranian market data)
- xrate.adapters.providers.navasan (NavasanProvider for fallback Iranian market data)
- xrate.adapters.providers.base (RateProvider protocol)
- xrate.domain.models (IrrSnapshot domain model)
"""
from __future__ import annotations  # Enable postponed evaluation of annotations

from typing import Mapping, Optional, Protocol  # Type hints for mappings, optional values, and protocols

from xrate.domain.models import IrrSnapshot  # Domain model for Iranian market snapshot
from xrate.adapters.providers.navasan import NavasanProvider  # Navasan API provider for market data
from xrate.adapters.providers.brsapi import BRSAPIProvider  # BRS API provider for market data


# RateProvider protocol for type checking
class RateProvider(Protocol):
    """Protocol for exchange rate providers."""
    def eur_usd_rate(self) -> float:  # returns USD per 1 EUR
        ...


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


class ProviderChain(RateProvider):
    """
    Provider chain that tries multiple providers in order.
    Tries BRS first, then FastForex for EUR/USD rates.
    Tracks which provider was actually used.
    """
    def __init__(self, primary: RateProvider, fallback: RateProvider):
        """
        Initialize provider chain with primary and fallback providers.
        
        Args:
            primary: Primary provider to try first (BRS API)
            fallback: Fallback provider to use if primary fails (FastForex)
        """
        self.primary = primary
        self.fallback = fallback
        self.last_used_provider: Optional[str] = None

    def eur_usd_rate(self) -> float:
        """
        Get EUR/USD rate, trying primary provider first, then fallback.
        Tracks which provider was used.
        
        Returns:
            USD per 1 EUR as float
            
        Raises:
            RuntimeError: If both providers fail
        """
        import logging
        log = logging.getLogger(__name__)
        try:
            rate = self.primary.eur_usd_rate()
            self.last_used_provider = "brsapi"
            return rate
        except Exception as e:
            log.warning("Primary provider (BRS) failed, trying fallback (FastForex): %s", e)
            try:
                rate = self.fallback.eur_usd_rate()
                self.last_used_provider = "fastforex"
                return rate
            except Exception as e2:
                log.error("Both providers failed. Primary: %s, Fallback: %s", e, e2)
                raise RuntimeError(f"All providers failed: primary={e}, fallback={e2}") from e2
    
    def get_last_provider(self) -> Optional[str]:
        """
        Get the name of the last provider that successfully provided data.
        
        Returns:
            Provider name ('brsapi' or 'fastforex') or None if not yet called
        """
        return self.last_used_provider


class RatesService:
    """
    High-level domain service for fetching and composing market data.
    The current use-case only needs EUR→USD; extend as needed.
    """
    def __init__(self, provider: RateProvider):
        """
        Initialize rates service with a provider.
        
        Args:
            provider: RateProvider instance (typically a ProviderChain)
        """
        self.provider = provider

    def eur_usd(self) -> Optional[float]:
        """
        Get USD per 1 EUR from the provider chain.
        
        Returns:
            USD per 1 EUR as float, or None if all providers fail
        """
        try:
            return self.provider.eur_usd_rate()
        except Exception:
            import logging
            log = logging.getLogger(__name__)
            log.warning("Failed to fetch EUR/USD rate from provider chain, returning None")
            return None
    
    def get_eur_usd_provider(self) -> Optional[str]:
        """
        Get the name of the provider that provided the EUR/USD rate.
        
        Returns:
            Provider name ('brsapi' or 'fastforex') or None if not available
        """
        if hasattr(self.provider, 'get_last_provider'):
            return self.provider.get_last_provider()
        return None


def get_irr_snapshot() -> Optional[IrrSnapshot]:
    """
    Fetch USD/EUR/18k Gold (IR market) from crawlers first, then fallback to API providers.
    
    Priority order:
    1. Crawlers (Bonbast, then AlanChand)
    2. BRS API
    3. Navasan API
    
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
        log.warning("Crawler service failed, falling back to API providers: %s", e)
    
    # Fallback to BRS API
    try:
        brs_provider = BRSAPIProvider()
        usd_toman = brs_provider.get_usd_toman()
        eur_toman = brs_provider.get_eur_toman()
        gold_1g_toman = brs_provider.get_gold_18k_toman()
        
        # Check if we got valid data
        if usd_toman and eur_toman and gold_1g_toman:
            log.info("Successfully fetched IRR snapshot from BRS API")
            return IrrSnapshot(
                usd_toman=usd_toman,
                eur_toman=eur_toman,
                gold_1g_toman=gold_1g_toman,
                provider="brsapi",
            )
        else:
            log.warning("BRS API returned incomplete data, trying Navasan fallback")
    except Exception as e:
        log.warning("BRS API failed, trying Navasan fallback: %s", e)
    
    # Final fallback to Navasan
    try:
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
        log.error("All sources failed. Crawlers, BRS API, and Navasan all failed. Last error: %s", e)
        return None
