# src/xrate/adapters/providers/wallex.py
"""
Wallex API Provider for Tether (USDT-TMN) Market Data

This module implements the Wallex API client for fetching Tether (USDT-TMN) market data
including the current price and 24-hour change percentage. It provides caching and
comprehensive error handling.

Files that USE this module:
- xrate.adapters.telegram.jobs (uses WallexProvider for Tether monitoring)
- tests.test_providers (unit tests)

Files that this module USES:
- xrate.config (settings for API configuration)
"""
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from xrate.config import settings

log = logging.getLogger(__name__)


class WallexProvider:
    """
    Wallex API provider for fetching Tether (USDT-TMN) market data.
    
    The API returns a JSON with market data for various trading pairs.
    We extract the USDTTMN symbol which contains Tether price in Toman
    and the 24-hour change percentage.
    """

    # Class-level cache shared across instances
    _cache_data: Optional[Dict[str, Any]] = None
    _cache_ts: Optional[datetime] = None

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize Wallex API provider.
        
        Args:
            base_url: Optional custom API URL (defaults to settings.WALLEX_URL)
            timeout: Optional HTTP timeout in seconds (defaults to settings.HTTP_TIMEOUT_SECONDS)
        """
        self.url = base_url or settings.WALLEX_URL  # Uses property with backward compat
        self.timeout = timeout or settings.http_timeout_seconds
        self.ttl = timedelta(minutes=settings.wallex_cache_minutes)

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
        Get the raw JSON dictionary from Wallex API (with TTL cache).
        
        Returns:
            Dictionary containing result.symbols with market data
            
        Raises:
            RuntimeError: If API request fails, returns invalid JSON, or missing required fields
        """
        if self._cache_valid():
            log.debug("Using cached Wallex API data")
            return self._cache_data  # type: ignore[return-value]

        try:
            log.info("Fetching fresh data from Wallex API")
            resp = requests.get(self.url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            log.error("Wallex API timeout after %d seconds", self.timeout)
            raise RuntimeError(f"Wallex API timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            log.error("Wallex API request failed: %s", e)
            raise RuntimeError(f"Wallex API request failed: {e}")
        except ValueError as e:
            log.error("Wallex API returned invalid JSON: %s", e)
            raise RuntimeError(f"Wallex API returned invalid JSON: {e}")

        # Validate response structure
        if not isinstance(data, dict):
            log.error("Wallex API unexpected response type: %r", type(data))
            raise RuntimeError("Wallex API returned non-dict JSON")

        # Validate required fields
        if "result" not in data:
            log.error("Wallex API missing 'result' field")
            raise RuntimeError("Wallex API response missing 'result' field")
        
        if "symbols" not in data["result"]:
            log.error("Wallex API missing 'result.symbols' field")
            raise RuntimeError("Wallex API response missing 'result.symbols' field")

        # Store in cache
        WallexProvider._cache_data = data
        WallexProvider._cache_ts = datetime.now(timezone.utc)
        log.info("Wallex API data updated (ttl=%sm)", settings.wallex_cache_minutes)
        return data

    def get_tether_data(self) -> Optional[Dict[str, Any]]:
        """
        Get Tether (USDT-TMN) market data from Wallex API.
        
        Returns:
            Dictionary with 'price' (float) and '24h_ch' (float) if available, None otherwise
            Price is in Toman, 24h_ch is percentage change
        """
        try:
            data = self.get_latest_raw()
            symbols = data.get("result", {}).get("symbols", {})
            usdttmn = symbols.get("USDTTMN")
            
            if not usdttmn:
                log.warning("USDTTMN not found in Wallex API response")
                return None
            
            stats = usdttmn.get("stats", {})
            last_price = stats.get("lastPrice")
            ch_24h = stats.get("24h_ch")
            
            if last_price is None or ch_24h is None:
                log.warning("USDTTMN stats missing lastPrice or 24h_ch")
                return None
            
            try:
                price = float(last_price)
                change_24h = float(ch_24h)
                
                log.info("Wallex API: USDT-TMN price=%s, 24h_ch=%s%%", price, change_24h)
                return {
                    "price": price,
                    "24h_ch": change_24h
                }
            except (ValueError, TypeError) as e:
                log.error("Failed to parse Wallex price or 24h_ch: %s", e)
                return None
                
        except Exception as e:
            log.error("Failed to get Tether data from Wallex API: %s", e)
            return None

    def get_tether_price_toman(self) -> Optional[int]:
        """
        Get Tether (USDT) price in Toman from Wallex API.
        
        Returns:
            USDT price in Toman as integer, or None if unavailable
        """
        data = self.get_tether_data()
        if data and "price" in data:
            return int(data["price"])
        return None

    def get_tether_24h_change(self) -> Optional[float]:
        """
        Get Tether (USDT-TMN) 24-hour change percentage from Wallex API.
        
        Returns:
            24-hour change percentage as float (e.g., -0.04 means -0.04%), or None if unavailable
        """
        data = self.get_tether_data()
        if data and "24h_ch" in data:
            return float(data["24h_ch"])
        return None

