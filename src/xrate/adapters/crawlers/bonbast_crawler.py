# src/xrate/adapters/crawlers/bonbast_crawler.py
"""
Bonbast.com Crawler

Crawler for fetching USD, EUR, and GoldGram sell prices from bonbast.com.
Parses HTML tables to extract currency and gold prices.

Files that USE this module:
- xrate.application.crawler_service (get_crawler_snapshot uses BonbastCrawler)
- xrate.adapters.telegram.jobs (crawler1_job creates BonbastCrawler instance)

Files that this module USES:
- xrate.adapters.crawlers.base (BaseCrawler base class, CrawlerResult dataclass)
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

import logging  # Standard library for logging messages
import re  # Regular expressions for finding price patterns in text

from typing import Optional  # Type hints for optional return values

from bs4 import BeautifulSoup  # HTML parsing library for extracting data from web pages

from xrate.adapters.crawlers.base import BaseCrawler, CrawlerResult  # Base crawler class and result dataclass

log = logging.getLogger(__name__)  # Create logger for this module


class BonbastCrawler(BaseCrawler):
    """
    Crawler for bonbast.com website.
    
    Extracts USD, EUR sell prices and GoldGram sell price from the HTML table.
    """
    
    def _parse_html(self, html: str) -> CrawlerResult:
        """
        Parse bonbast.com HTML to extract prices.
        
        The website shows a table with currency codes and sell prices.
        We look for USD, EUR rows and extract the sell price.
        For gold, we look for "Gold Gram" or similar.
        
        Args:
            html: HTML content from bonbast.com
            
        Returns:
            CrawlerResult with extracted prices
        """
        soup = BeautifulSoup(html, "html.parser")
        
        usd_sell: Optional[int] = None
        eur_sell: Optional[int] = None
        gold_gram_sell: Optional[int] = None
        
        # Find all tables on the page
        tables = soup.find_all("table")
        
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue
                
                # Check first cell for currency code or name
                first_cell_text = cells[0].get_text(strip=True).upper()
                
                # Look for USD
                if "USD" in first_cell_text or "US DOLLAR" in first_cell_text:
                    sell_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    usd_sell = self._parse_price(sell_text)
                    if usd_sell:
                        log.debug("Found USD sell price: %d", usd_sell)
                
                # Look for EUR
                elif "EUR" in first_cell_text or "EURO" in first_cell_text:
                    sell_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    eur_sell = self._parse_price(sell_text)
                    if eur_sell:
                        log.debug("Found EUR sell price: %d", eur_sell)
                
                # Look for Gold Gram
                elif "GOLD" in first_cell_text and "GRAM" in first_cell_text:
                    sell_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    gold_gram_sell = self._parse_price(sell_text)
                    if gold_gram_sell:
                        log.debug("Found GoldGram sell price: %d", gold_gram_sell)
        
        # If not found in tables, try alternative selectors
        if not usd_sell or not eur_sell:
            # Look for data attributes or specific classes
            usd_elements = soup.find_all(string=re.compile(r"USD|US\s*DOLLAR", re.I))
            eur_elements = soup.find_all(string=re.compile(r"EUR|EURO", re.I))
            
            # Try to find nearby sell prices
            for elem in usd_elements:
                parent = elem.find_parent()
                if parent:
                    # Look for sell price in nearby cells or siblings
                    sell_elem = parent.find_next_sibling()
                    if sell_elem:
                        price = self._parse_price(sell_elem.get_text())
                        if price and not usd_sell:
                            usd_sell = price
            
            for elem in eur_elements:
                parent = elem.find_parent()
                if parent:
                    sell_elem = parent.find_next_sibling()
                    if sell_elem:
                        price = self._parse_price(sell_elem.get_text())
                        if price and not eur_sell:
                            eur_sell = price
        
        # Look for gold price in alternative locations
        if not gold_gram_sell:
            gold_elements = soup.find_all(string=re.compile(r"Gold.*Gram|Gram.*Gold", re.I))
            for elem in gold_elements:
                parent = elem.find_parent()
                if parent:
                    # Look for price nearby
                    price_elem = parent.find_next_sibling()
                    if price_elem:
                        price = self._parse_price(price_elem.get_text())
                        if price:
                            gold_gram_sell = price
                            break
        
        if not usd_sell and not eur_sell and not gold_gram_sell:
            log.warning("Could not extract any prices from bonbast.com HTML")
        
        return CrawlerResult(
            usd_sell=usd_sell,
            eur_sell=eur_sell,
            gold_gram_sell=gold_gram_sell,
            timestamp=None,  # Will be set by base class
        )

