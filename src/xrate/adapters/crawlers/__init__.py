# src/xrate/adapters/crawlers/__init__.py
"""
Web Crawlers for Exchange Rate Data

This package contains web crawlers that fetch exchange rates from websites
by parsing HTML content. Crawlers implement caching to prevent too frequent
requests and avoid being banned.
"""

from xrate.adapters.crawlers.bonbast_crawler import BonbastCrawler
from xrate.adapters.crawlers.alanchand_crawler import AlanChandCrawler

__all__ = ["BonbastCrawler", "AlanChandCrawler"]

