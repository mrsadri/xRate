# src/xrate/adapters/providers/navasan.py
"""
Navasan API Provider for Iranian Market Data

This module implements the Navasan API client for fetching Iranian market data
including USD/EUR rates in Toman and gold prices. It provides caching and
flexible data extraction capabilities.

Files that USE this module:
- xrate.application.rates_service (get_irr_snapshot function uses NavasanProvider)
- tests.test_providers (unit tests)
- tests.test_rates_service (integration tests)

Files that this module USES:
- xrate.config (settings for API configuration)
"""
import json
import logging
import urllib.parse
from typing import Any, Dict, Iterable, Optional
from datetime import datetime, timedelta, timezone

import requests

from xrate.config import settings

log = logging.getLogger(__name__)


class NavasanProvider:
    """
    Lightweight client for Navasan 'latest' endpoint.

    It fetches a large JSON object and lets you extract the keys you care about.
    Each key is usually an object like:
      {"value": "108400", "change": 1100, "timestamp": ..., "date": "..."}
    """

    # Class-level cache shared across instances
    _cache_data: Optional[Dict[str, Any]] = None
    _cache_ts: Optional[datetime] = None

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize Navasan API provider.
        
        Args:
            base_url: Optional custom API URL (defaults to settings.NAVASAN_URL)
            timeout: Optional HTTP timeout in seconds (defaults to settings.HTTP_TIMEOUT_SECONDS)
            
        Raises:
            ValueError: If API URL is missing or API key is empty
        """
        self.url = base_url or settings.NAVASAN_URL  # Uses property with backward compat
        if not self.url or "api_key=" not in self.url:
            raise ValueError("NAVASAN_URL is missing or api_key not configured in .env.")
        # Check that api_key has a non-empty value (not just "api_key=")
        parsed = urllib.parse.urlparse(self.url)
        params = urllib.parse.parse_qs(parsed.query)
        if "api_key" not in params or not params["api_key"] or not params["api_key"][0]:
            raise ValueError("NAVASAN_URL contains empty api_key value.")
        self.timeout = timeout or settings.http_timeout_seconds
        self.ttl = timedelta(minutes=settings.navasan_cache_minutes)

    @staticmethod
    def _extract_value(node: Any) -> Optional[str]:
        """
        Normalize different shapes into a printable string:
        - If a dict, prefer 'value'; otherwise stringify the dict (useful for debugging).
        - If primitive (int/float/str), cast to str.
        """
        if node is None:
            return None
        if isinstance(node, dict):
            if "value" in node and node["value"] is not None:
                return str(node["value"])
            # Fallback: compact JSON string for visibility
            return json.dumps(node, ensure_ascii=False)
        return str(node)

    def _cache_valid(self) -> bool:
        """
        Check if cached data is still valid based on TTL.
        
        Returns:
            True if cache exists and is within TTL, False otherwise
        """
        if self._cache_data is None or self._cache_ts is None:
            return False
        return datetime.now(timezone.utc) - self._cache_ts < self.ttl

    def get_latest_raw(self) -> Dict[str, Any]:
        """
        Get the raw JSON dictionary from Navasan /latest endpoint (with TTL cache).
        
        Returns:
            Dictionary containing all market data from Navasan API
            
        Raises:
            RuntimeError: If API request fails or returns invalid data
        """
        if self._cache_valid():
            log.debug("Using cached Navasan data")
            return self._cache_data  # type: ignore[return-value]

        try:
            log.info("Fetching fresh data from Navasan API")
            resp = requests.get(self.url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            log.error("Navasan API timeout after %d seconds", self.timeout)
            raise RuntimeError(f"Navasan API timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            log.error("Navasan API request failed: %s", e)
            raise RuntimeError(f"Navasan API request failed: {e}")
        except ValueError as e:
            log.error("Navasan API returned invalid JSON: %s", e)
            raise RuntimeError(f"Navasan API returned invalid JSON: {e}")

        if not isinstance(data, dict):
            log.error("Navasan unexpected response type: %r", type(data))
            raise RuntimeError("Navasan returned non-dict JSON")

        # store in cache
        NavasanProvider._cache_data = data
        NavasanProvider._cache_ts = datetime.now(timezone.utc)
        log.info("Navasan data updated (ttl=%sm)", settings.navasan_cache_minutes)
        return data

    def get_values(self, keys: Iterable[str]) -> Dict[str, str]:
        """
        Extract specific values from Navasan API data.
        
        Args:
            keys: Iterable of keys to extract from the API response
            
        Returns:
            Dictionary mapping keys to their string values.
            Missing keys are returned as 'NOT_FOUND'.
        """
        data = self.get_latest_raw()
        out: Dict[str, str] = {}
        for k in keys:
            out[k] = self._extract_value(data.get(k)) or "NOT_FOUND"
        log.debug("Navasan values fetched: %s", out)
        return out
