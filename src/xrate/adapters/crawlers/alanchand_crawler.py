# src/xrate/adapters/crawlers/alanchand_crawler.py
"""
AlanChand.com Crawler

Crawler for fetching USD, EUR, and GoldGram sell prices from alanchand.com.
Parses HTML tables to extract currency and gold prices (supports Persian/Farsi text).

Files that USE this module:
- xrate.application.crawler_service (get_crawler_snapshot uses AlanChandCrawler)
- xrate.adapters.telegram.jobs (crawler2_job creates AlanChandCrawler instance)

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


class AlanChandCrawler(BaseCrawler):
    """
    Crawler for alanchand.com website.
    
    Extracts USD, EUR sell prices and GoldGram sell price from the HTML table.
    """
    
    def _parse_html(self, html: str) -> CrawlerResult:
        """
        Parse alanchand.com HTML to extract prices.
        
        The website shows a table with currency names and sell prices.
        We look for USD, EUR rows and extract the sell price.
        For gold, we look for "گرم طلای 18 عیار" or "Gold Gram".
        
        Args:
            html: HTML content from alanchand.com
            
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
                
                # Check first cell for currency name (can be in Persian or English)
                first_cell_text = cells[0].get_text(strip=True)
                
                # Look for USD (دلار آمریکا or USD)
                if "دلار آمریکا" in first_cell_text or "USD" in first_cell_text.upper() or "US DOLLAR" in first_cell_text.upper():
                    # Sell price is typically in the second or third column
                    sell_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    if not sell_text or sell_text == "-":
                        sell_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    usd_sell = self._parse_price(sell_text)
                    if usd_sell:
                        log.debug("Found USD sell price: %d", usd_sell)
                
                # Look for EUR (یورو or EUR)
                elif "یورو" in first_cell_text or "EUR" in first_cell_text.upper() or "EURO" in first_cell_text.upper():
                    sell_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    if not sell_text or sell_text == "-":
                        sell_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    eur_sell = self._parse_price(sell_text)
                    if eur_sell:
                        log.debug("Found EUR sell price: %d", eur_sell)
                
                # Look for Gold Gram (گرم طلای 18 عیار or similar)
                elif "طلا" in first_cell_text and ("18" in first_cell_text or "عیار" in first_cell_text or "گرم" in first_cell_text):
                    sell_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    if not sell_text or sell_text == "-":
                        sell_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    gold_gram_sell = self._parse_price(sell_text)
                    if gold_gram_sell:
                        log.debug("Found GoldGram sell price: %d", gold_gram_sell)
        
        # Alternative: Look for specific text patterns in the page
        if not usd_sell:
            usd_elements = soup.find_all(string=re.compile(r"دلار آمریکا|USD|US\s*DOLLAR", re.I))
            for elem in usd_elements:
                parent = elem.find_parent()
                if parent:
                    # Look for price in nearby elements
                    price_elem = parent.find_next(["td", "span", "div"])
                    if price_elem:
                        price = self._parse_price(price_elem.get_text())
                        if price:
                            usd_sell = price
                            break
        
        if not eur_sell:
            eur_elements = soup.find_all(string=re.compile(r"یورو|EUR|EURO", re.I))
            for elem in eur_elements:
                parent = elem.find_parent()
                if parent:
                    price_elem = parent.find_next(["td", "span", "div"])
                    if price_elem:
                        price = self._parse_price(price_elem.get_text())
                        if price:
                            eur_sell = price
                            break
        
        if not gold_gram_sell:
            gold_elements = soup.find_all(string=re.compile(r"گرم طلای|Gold.*Gram|Gram.*Gold", re.I))
            for elem in gold_elements:
                parent = elem.find_parent()
                if parent:
                    price_elem = parent.find_next(["td", "span", "div"])
                    if price_elem:
                        price = self._parse_price(price_elem.get_text())
                        if price:
                            gold_gram_sell = price
                            break
        
        if not usd_sell and not eur_sell and not gold_gram_sell:
            log.warning("Could not extract any prices from alanchand.com HTML")
        
        return CrawlerResult(
            usd_sell=usd_sell,
            eur_sell=eur_sell,
            gold_gram_sell=gold_gram_sell,
            timestamp=None,  # Will be set by base class
        )

