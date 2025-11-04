# src/xrate/application/crawler_service.py
"""
Crawler Service - Fetch prices from web crawlers with API fallback

This service provides a unified interface to fetch market prices, trying
crawlers first (Bonbast, AlanChand), then falling back to API providers
if crawlers are unavailable.

Files that USE this module:
- xrate.application.rates_service (get_irr_snapshot uses get_crawler_snapshot)
- xrate.adapters.telegram.jobs (crawler jobs use crawlers directly)

Files that this module USES:
- xrate.domain.models (IrrSnapshot domain model)
- xrate.adapters.crawlers.bonbast_crawler (BonbastCrawler for bonbast.com)
- xrate.adapters.crawlers.alanchand_crawler (AlanChandCrawler for alanchand.com)
- xrate.config (settings for crawler configuration)
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

import logging  # Standard library for logging messages

from typing import Optional  # Type hints for optional return values

from xrate.domain.models import IrrSnapshot  # Domain model for Iranian market snapshot
from xrate.adapters.crawlers.bonbast_crawler import BonbastCrawler  # Crawler for bonbast.com website
from xrate.adapters.crawlers.alanchand_crawler import AlanChandCrawler  # Crawler for alanchand.com website
from xrate.config import settings  # Application configuration and settings

log = logging.getLogger(__name__)  # Create logger for this module


def get_crawler_snapshot() -> Optional[IrrSnapshot]:
    """
    Fetch USD/EUR/Gold prices from crawlers (Bonbast first, then AlanChand).
    
    Tries both crawlers and returns the first successful result.
    If both fail, returns None (will fallback to API providers).
    
    Returns:
        IrrSnapshot with prices from crawler, or None if both crawlers fail
    """
    # Try Crawler1 (Bonbast) first
    try:
        crawler1 = BonbastCrawler(
            url=settings.crawler1_url,
            cache_minutes=settings.crawler1_interval_minutes,
            timeout=settings.http_timeout_seconds,
        )
        result1 = crawler1.fetch()
        
        # Check if we got all required prices
        if result1.usd_sell and result1.eur_sell and result1.gold_gram_sell:
            log.info("Successfully fetched prices from Crawler1 (Bonbast): USD=%d, EUR=%d, Gold=%d",
                    result1.usd_sell, result1.eur_sell, result1.gold_gram_sell)
            return IrrSnapshot(
                usd_toman=result1.usd_sell,
                eur_toman=result1.eur_sell,
                gold_1g_toman=result1.gold_gram_sell,
                provider="crawler1_bonbast",
            )
        else:
            log.warning("Crawler1 (Bonbast) returned incomplete data, trying Crawler2")
    except Exception as e:
        log.warning("Crawler1 (Bonbast) failed, trying Crawler2: %s", e)
    
    # Fallback to Crawler2 (AlanChand)
    try:
        crawler2 = AlanChandCrawler(
            url=settings.crawler2_url,
            cache_minutes=settings.crawler2_interval_minutes,
            timeout=settings.http_timeout_seconds,
        )
        result2 = crawler2.fetch()
        
        # Check if we got all required prices
        if result2.usd_sell and result2.eur_sell and result2.gold_gram_sell:
            log.info("Successfully fetched prices from Crawler2 (AlanChand): USD=%d, EUR=%d, Gold=%d",
                    result2.usd_sell, result2.eur_sell, result2.gold_gram_sell)
            return IrrSnapshot(
                usd_toman=result2.usd_sell,
                eur_toman=result2.eur_sell,
                gold_1g_toman=result2.gold_gram_sell,
                provider="crawler2_alanchand",
            )
        else:
            log.warning("Crawler2 (AlanChand) returned incomplete data")
    except Exception as e:
        log.warning("Crawler2 (AlanChand) failed: %s", e)
    
    # Both crawlers failed
    log.info("All crawlers failed, will fallback to API providers")
    return None

