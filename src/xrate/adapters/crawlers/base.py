# src/xrate/adapters/crawlers/base.py
"""
Base Crawler with Caching Mechanism

This module provides a base class for web crawlers with built-in caching
to prevent too frequent requests and avoid being banned by websites.

Files that USE this module:
- xrate.adapters.crawlers.bonbast_crawler (BonbastCrawler extends BaseCrawler)
- xrate.adapters.crawlers.alanchand_crawler (AlanChandCrawler extends BaseCrawler)
- xrate.application.crawler_service (uses crawler classes)

Files that this module USES:
- None (pure base class with minimal dependencies)
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

import logging  # Standard library for logging messages
import re  # Regular expressions for parsing text patterns
from abc import ABC, abstractmethod  # Abstract base classes for defining interfaces
from dataclasses import dataclass  # Decorator for creating data classes
from datetime import datetime, timedelta, timezone  # Date/time utilities for caching timestamps
from typing import Optional  # Type hints for optional values

import requests  # HTTP library for making web requests

log = logging.getLogger(__name__)  # Create logger for this module


@dataclass(frozen=True)
class CrawlerResult:
    """Result from a crawler fetch operation."""
    
    usd_sell: Optional[int] = None
    eur_sell: Optional[int] = None
    gold_gram_sell: Optional[int] = None
    timestamp: Optional[datetime] = None


class BaseCrawler(ABC):
    """
    Base class for web crawlers with TTL-based caching.
    
    Implements caching at the class level to prevent multiple requests
    within the cache TTL window, protecting against rate limiting and bans.
    """
    
    # Class-level cache shared across instances
    _cache_data: Optional[CrawlerResult] = None
    _cache_ts: Optional[datetime] = None
    
    def __init__(
        self,
        url: str,
        cache_minutes: int,
        timeout: int = 10,
    ):
        """
        Initialize base crawler.
        
        Args:
            url: URL to crawl
            cache_minutes: Cache TTL in minutes (minimum time between requests)
            timeout: HTTP request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self.ttl = timedelta(minutes=cache_minutes)
    
    def _cache_valid(self) -> bool:
        """
        Check if cached data is still valid based on TTL.
        
        Returns:
            True if cache exists and is within TTL, False otherwise
        """
        if self._cache_data is None or self._cache_ts is None:
            return False
        return datetime.now(timezone.utc) - self._cache_ts < self.ttl
    
    def _fetch_html(self) -> str:
        """
        Fetch HTML content from the URL.
        
        Returns:
            HTML content as string
            
        Raises:
            RuntimeError: If request fails or times out
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            log.info("Fetching HTML from %s", self.url)
            resp = requests.get(self.url, timeout=self.timeout, headers=headers)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.Timeout:
            log.error("Crawler timeout after %d seconds for %s", self.timeout, self.url)
            raise RuntimeError(f"Crawler timeout after {self.timeout}s for {self.url}")
        except requests.exceptions.RequestException as e:
            log.error("Crawler request failed for %s: %s", self.url, e)
            raise RuntimeError(f"Crawler request failed for {self.url}: {e}")
    
    @abstractmethod
    def _parse_html(self, html: str) -> CrawlerResult:
        """
        Parse HTML content and extract prices.
        
        Args:
            html: HTML content to parse
            
        Returns:
            CrawlerResult with extracted prices
        """
        raise NotImplementedError
    
    def _parse_price(self, text: str) -> Optional[int]:
        """
        Parse price from text string.
        
        Removes commas, spaces, and converts to integer.
        Handles Persian/Farsi digits if present.
        This is a shared utility method for all crawlers.
        
        Args:
            text: Text containing price
            
        Returns:
            Integer price or None if parsing fails
        """
        if not text:
            return None
        
        # Remove common separators
        text = text.replace(",", "").replace(" ", "").replace("،", "").strip()
        
        # Convert Persian digits to English digits
        persian_digits = {
            "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
            "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9"
        }
        for persian, english in persian_digits.items():
            text = text.replace(persian, english)
        
        # Extract numbers using regex
        numbers = re.findall(r"\d+", text)
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass
        
        return None
    
    def fetch(self) -> CrawlerResult:
        """
        Fetch and parse prices from the website.
        
        Uses caching to prevent too frequent requests. If cache is valid,
        returns cached data. Otherwise, fetches fresh data and updates cache.
        
        Returns:
            CrawlerResult with prices
            
        Raises:
            RuntimeError: If fetch or parsing fails
        """
        # Check cache first
        if self._cache_valid():
            log.debug("Using cached crawler data for %s", self.url)
            return self._cache_data  # type: ignore[return-value]
        
        # Fetch fresh data
        try:
            html = self._fetch_html()
            result = self._parse_html(html)
            
            # Update cache
            type(self)._cache_data = result
            type(self)._cache_ts = datetime.now(timezone.utc)
            log.info("Crawler data updated for %s (ttl=%s minutes)", self.url, self.ttl.total_seconds() / 60)
            
            return result
        except Exception as e:
            log.error("Failed to fetch or parse data from %s: %s", self.url, e, exc_info=True)
            raise RuntimeError(f"Failed to fetch or parse data from {self.url}: {e}")

