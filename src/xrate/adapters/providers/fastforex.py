# src/xrate/adapters/providers/fastforex.py
"""
FastForex API Provider for EUR→USD Exchange Rates

This module implements the FastForex API client for fetching EUR→USD exchange rates.
It provides caching functionality to reduce API calls and includes comprehensive error handling.

Files that USE this module:
- xrate.application.rates_service (RatesService uses FastForexProvider)
- tests.test_providers (unit tests)

Files that this module USES:
- xrate.adapters.providers.base (RateProvider interface)
- xrate.config (settings for API configuration)
"""
import logging
import urllib.parse
import requests
from typing import Optional
from datetime import datetime, timedelta, timezone

from xrate.adapters.providers.base import RateProvider
from xrate.config import settings

log = logging.getLogger(__name__)


class FastForexProvider(RateProvider):
    # Class-level cache shared across instances
    _cache_rate: Optional[float] = None
    _cache_ts: Optional[datetime] = None

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize FastForex API provider.
        
        Args:
            base_url: Optional custom API URL (defaults to settings.FASTFOREX_URL)
            timeout: Optional HTTP timeout in seconds (defaults to settings.HTTP_TIMEOUT_SECONDS)
            
        Raises:
            ValueError: If API key is missing or empty in the URL
        """
        self.url = base_url or settings.FASTFOREX_URL  # Uses property with backward compat
        # Validate that api_key has a non-empty value
        parsed = urllib.parse.urlparse(self.url)
        params = urllib.parse.parse_qs(parsed.query)
        if "api_key" not in params or not params["api_key"] or not params["api_key"][0]:
            raise ValueError("FASTFOREX_URL contains empty or missing api_key value.")
        self.timeout = timeout or settings.http_timeout_seconds
        self.ttl = timedelta(minutes=settings.fastforex_cache_minutes)

    def _cache_valid(self) -> bool:
        """
        Check if cached rate is still valid based on TTL.
        
        Returns:
            True if cache exists and is within TTL, False otherwise
        """
        if self._cache_rate is None or self._cache_ts is None:
            return False
        return datetime.now(timezone.utc) - self._cache_ts < self.ttl

    def eur_usd_rate(self) -> float:
        """
        Get EUR/USD exchange rate from FastForex API.
        
        FastForex returns EUR per USD, which is inverted to get USD per EUR.
        Uses a TTL cache defined by FASTFOREX_CACHE_MINUTES.
        
        Returns:
            USD per 1 EUR as float
            
        Raises:
            RuntimeError: If API request fails, returns invalid data, or rate is non-positive
        """
        if self._cache_valid():
            log.debug("Using cached FastForex rate: %s", self._cache_rate)
            return self._cache_rate  # type: ignore[return-value]

        try:
            log.info("Fetching fresh EUR/USD rate from FastForex")
            resp = requests.get(self.url, timeout=self.timeout)
            
            # Check for 5xx errors (server errors) - these should trigger fallback
            if resp.status_code >= 500:
                log.warning("FastForex API returned 5xx error (%d), will trigger fallback", resp.status_code)
                raise RuntimeError(f"FastForex API returned {resp.status_code} (server error)")
            
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            log.warning("FastForex API timeout after %d seconds, will trigger fallback", self.timeout)
            raise RuntimeError(f"FastForex API timeout after {self.timeout}s")
        except requests.exceptions.HTTPError as e:
            # 5xx errors should trigger fallback, 4xx are client errors (don't retry)
            if e.response and e.response.status_code >= 500:
                log.warning("FastForex API HTTP error %d (server error), will trigger fallback", e.response.status_code)
                raise RuntimeError(f"FastForex API HTTP {e.response.status_code} (server error)") from e
            log.error("FastForex API HTTP error: %s", e)
            raise RuntimeError(f"FastForex API HTTP error: {e}") from e
        except requests.exceptions.RequestException as e:
            log.warning("FastForex API request failed (network/connection error), will trigger fallback: %s", e)
            raise RuntimeError(f"FastForex API request failed: {e}") from e
        except ValueError as e:
            log.error("FastForex API returned invalid JSON: %s", e)
            raise RuntimeError(f"FastForex API returned invalid JSON: {e}")

        try:
            # Expect: {"base":"USD","results":{"EUR":0.86...}}
            if "results" not in data or "EUR" not in data["results"]:
                log.error("FastForex unexpected response structure: %s", data)
                raise RuntimeError("FastForex response missing 'results.EUR' field")
            
            eur_per_usd = float(data["results"]["EUR"])
        except (KeyError, ValueError, TypeError) as e:
            log.error("FastForex unexpected schema: %s", data)
            raise RuntimeError(f"FastForex schema error: {e}") from e

        if eur_per_usd <= 0:
            log.error("FastForex returned non-positive EUR/USD: %s", eur_per_usd)
            raise RuntimeError(f"FastForex returned non-positive EUR/USD: {eur_per_usd}")

        usd_per_eur = 1.0 / eur_per_usd

        # cache
        FastForexProvider._cache_rate = usd_per_eur
        FastForexProvider._cache_ts = datetime.now(timezone.utc)

        log.info(
            "FastForex updated: EUR per USD=%s → USD per EUR=%s (ttl=%sm)",
            eur_per_usd, usd_per_eur, settings.fastforex_cache_minutes
        )
        return usd_per_eur
