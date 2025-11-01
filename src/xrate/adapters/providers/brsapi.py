# src/xrate/adapters/providers/brsapi.py
"""
BRS API Provider for Iranian Market Data

This module implements the BRS API client for fetching Iranian market data
including USD/EUR rates in Toman and gold prices. It provides caching and
comprehensive error handling.

Files that USE this module:
- xrate.application.rates_service (uses BRSAPIProvider)
- tests.test_providers (unit tests)

Files that this module USES:
- xrate.adapters.providers.base (RateProvider interface)
- xrate.config (settings for API configuration)
"""
import logging
import urllib.parse
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from xrate.adapters.providers.base import RateProvider
from xrate.config import settings

log = logging.getLogger(__name__)


class BRSAPIProvider(RateProvider):
    """
    BRS API provider for fetching gold, currency, and cryptocurrency data.
    
    The API returns a JSON with three arrays:
    - gold: Iranian gold prices (IR_GOLD_18K, IR_GOLD_24K, etc.)
    - currency: Currency rates (USD, EUR, etc.) in Toman
    - cryptocurrency: Crypto prices
    """

    # Class-level cache shared across instances
    _cache_data: Optional[Dict[str, Any]] = None
    _cache_ts: Optional[datetime] = None

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize BRS API provider.
        
        Args:
            base_url: Optional custom API URL (defaults to settings.BRSAPI_URL)
            timeout: Optional HTTP timeout in seconds (defaults to settings.HTTP_TIMEOUT_SECONDS)
            
        Raises:
            ValueError: If API key is missing or empty in the URL
        """
        self.url = base_url or settings.BRSAPI_URL  # Uses property with backward compat
        # Validate that api_key has a non-empty value
        parsed = urllib.parse.urlparse(self.url)
        params = urllib.parse.parse_qs(parsed.query)
        if "key" not in params or not params["key"] or not params["key"][0]:
            raise ValueError("BRSAPI_URL contains empty or missing key value.")
        self.timeout = timeout or settings.http_timeout_seconds
        self.ttl = timedelta(minutes=settings.brsapi_cache_minutes)

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
        Get the raw JSON dictionary from BRS API (with TTL cache).
        
        Returns:
            Dictionary containing gold, currency, and cryptocurrency arrays
            
        Raises:
            RuntimeError: If API request fails, returns invalid JSON, or missing required fields
        """
        if self._cache_valid():
            log.debug("Using cached BRS API data")
            return self._cache_data  # type: ignore[return-value]

        try:
            log.info("Fetching fresh data from BRS API")
            resp = requests.get(self.url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            log.error("BRS API timeout after %d seconds", self.timeout)
            raise RuntimeError(f"BRS API timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            log.error("BRS API request failed: %s", e)
            raise RuntimeError(f"BRS API request failed: {e}")
        except ValueError as e:
            log.error("BRS API returned invalid JSON: %s", e)
            raise RuntimeError(f"BRS API returned invalid JSON: {e}")

        # The API returns a list with one object, or a direct object
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        elif not isinstance(data, dict):
            log.error("BRS API unexpected response type: %r", type(data))
            raise RuntimeError("BRS API returned non-dict JSON")

        # Validate required fields
        if "gold" not in data or "currency" not in data:
            log.error("BRS API missing required fields (gold/currency): %s", data.keys())
            raise RuntimeError("BRS API response missing required fields")

        # Store in cache
        BRSAPIProvider._cache_data = data
        BRSAPIProvider._cache_ts = datetime.now(timezone.utc)
        log.info("BRS API data updated (ttl=%sm)", settings.brsapi_cache_minutes)
        return data

    def _find_item_by_symbol(self, items: list, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Find an item in a list by its symbol field.
        
        Args:
            items: List of dictionaries to search
            symbol: Symbol to match against
            
        Returns:
            Matching dictionary item or None if not found
        """
        for item in items:
            if isinstance(item, dict) and item.get("symbol") == symbol:
                return item
        return None

    def get_usd_toman(self) -> Optional[int]:
        """
        Get USD price in Toman from BRS API.
        
        Returns:
            USD price in Toman as integer, or None if unavailable
        """
        try:
            data = self.get_latest_raw()
            currency_list = data.get("currency", [])
            usd_item = self._find_item_by_symbol(currency_list, "USD")
            if usd_item and "price" in usd_item:
                return int(float(usd_item["price"]))
            log.warning("USD not found in BRS API response")
            return None
        except Exception as e:
            log.error("Failed to get USD from BRS API: %s", e)
            return None

    def get_eur_toman(self) -> Optional[int]:
        """
        Get EUR price in Toman from BRS API.
        
        Returns:
            EUR price in Toman as integer, or None if unavailable
        """
        try:
            data = self.get_latest_raw()
            currency_list = data.get("currency", [])
            eur_item = self._find_item_by_symbol(currency_list, "EUR")
            if eur_item and "price" in eur_item:
                return int(float(eur_item["price"]))
            log.warning("EUR not found in BRS API response")
            return None
        except Exception as e:
            log.error("Failed to get EUR from BRS API: %s", e)
            return None

    def get_gold_18k_toman(self) -> Optional[int]:
        """
        Get 18K gold price per gram in Toman from BRS API.
        
        Returns:
            18K gold price per gram in Toman as integer, or None if unavailable
        """
        try:
            data = self.get_latest_raw()
            gold_list = data.get("gold", [])
            gold_item = self._find_item_by_symbol(gold_list, "IR_GOLD_18K")
            if gold_item and "price" in gold_item:
                return int(float(gold_item["price"]))
            log.warning("IR_GOLD_18K not found in BRS API response")
            return None
        except Exception as e:
            log.error("Failed to get gold from BRS API: %s", e)
            return None

    def eur_usd_rate(self) -> float:
        """
        Calculate EUR/USD rate from BRS API data.
        Returns USD per 1 EUR = (EUR in Toman) / (USD in Toman)
        """
        try:
            data = self.get_latest_raw()
            currency_list = data.get("currency", [])
            
            usd_item = self._find_item_by_symbol(currency_list, "USD")
            eur_item = self._find_item_by_symbol(currency_list, "EUR")
            
            if not usd_item or "price" not in usd_item:
                log.error("USD not found in BRS API response")
                raise RuntimeError("USD not found in BRS API response")
            if not eur_item or "price" not in eur_item:
                log.error("EUR not found in BRS API response")
                raise RuntimeError("EUR not found in BRS API response")
            
            usd_price = float(usd_item["price"])
            eur_price = float(eur_item["price"])
            
            if usd_price <= 0:
                log.error("BRS API returned non-positive USD price: %s", usd_price)
                raise RuntimeError(f"BRS API returned non-positive USD price: {usd_price}")
            if eur_price <= 0:
                log.error("BRS API returned non-positive EUR price: %s", eur_price)
                raise RuntimeError(f"BRS API returned non-positive EUR price: {eur_price}")
            
            usd_per_eur = eur_price / usd_price
            
            log.info("BRS API: EUR=%s Toman, USD=%s Toman → EUR/USD=%s", 
                     eur_price, usd_price, usd_per_eur)
            return usd_per_eur
            
        except Exception as e:
            log.error("Failed to calculate EUR/USD from BRS API: %s", e)
            raise RuntimeError(f"Failed to calculate EUR/USD from BRS API: {e}") from e
