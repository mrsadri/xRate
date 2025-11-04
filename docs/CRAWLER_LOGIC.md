# Crawler Price Fetching Logic

This document explains how the crawlers fetch new prices from websites.

## Overview

The system uses two web crawlers that run on separate schedules:
- **Crawler1 (Bonbast)**: Runs every 37 minutes (configurable)
- **Crawler2 (AlanChand)**: Runs every 43 minutes (configurable)

Both crawlers extract **USD sell price**, **EUR sell price**, and **GoldGram sell price** from their respective websites.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Scheduled Job Triggered (every 37/43 minutes)            │
│    - crawler1_job() or crawler2_job()                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Create Crawler Instance                                  │
│    - BonbastCrawler(url, cache_minutes=37, timeout=10)     │
│    - AlanChandCrawler(url, cache_minutes=43, timeout=10)   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Call crawler.fetch()                                     │
│    This is the main entry point                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Check Cache (_cache_valid())                              │
│    ┌─────────────────────────────────────────────┐          │
│    │ Is cache_data exists?                       │          │
│    │ AND                                          │          │
│    │ (current_time - cache_timestamp) < TTL?     │          │
│    └─────────────────────────────────────────────┘          │
│                      │                                       │
│         ┌────────────┴────────────┐                        │
│         │                         │                         │
│    YES (valid)              NO (expired/missing)            │
│         │                         │                         │
│         ▼                         ▼                         │
│    Return cached          Continue to fetch                 │
│    data (SKIP             fresh data                        │
│    network request)                                         │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Fetch HTML (_fetch_html())                                │
│    - HTTP GET request to website URL                        │
│    - User-Agent header to mimic browser                     │
│    - Timeout protection (10 seconds default)                │
│    - Returns HTML content as string                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Parse HTML (_parse_html())                                │
│    This is implemented differently for each crawler:         │
│                                                              │
│    BonbastCrawler:                                           │
│    - Find all <table> elements                               │
│    - Loop through <tr> rows                                 │
│    - Look for cells containing "USD", "EUR", "Gold Gram"     │
│    - Extract sell price from adjacent cells                  │
│                                                              │
│    AlanChandCrawler:                                         │
│    - Find all <table> elements                               │
│    - Loop through <tr> rows                                 │
│    - Look for cells containing "دلار آمریکا", "یورو", etc. │
│    - Extract sell price from adjacent cells                  │
│                                                              │
│    Both parsers:                                             │
│    - Handle Persian/Farsi digits (۰-۹ → 0-9)                │
│    - Remove commas and spaces                               │
│    - Extract first number found                              │
│    - Return CrawlerResult with prices                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Update Cache                                              │
│    - Store result in class-level _cache_data                │
│    - Store current timestamp in _cache_ts                   │
│    - Cache is shared across all instances                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Return Result                                             │
│    - CrawlerResult(usd_sell, eur_sell, gold_gram_sell)       │
│    - Log prices to logger                                    │
│    - Log warning if any price is missing                     │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. **Caching Protection** (Prevents Bans)

The cache prevents multiple requests within the TTL window:

```python
# Example: Crawler1 with 37-minute interval
# First call at 10:00 AM → Fetches from website → Caches result
# Second call at 10:15 AM → Returns cached data (no network request)
# Third call at 10:37 AM → Cache expired → Fetches fresh data
```

**Why this matters:**
- The job scheduler runs every 37 minutes (Crawler1) or 43 minutes (Crawler2)
- But if the job is called multiple times (e.g., manual trigger, restart), the cache prevents duplicate requests
- This protects against rate limiting and IP bans

### 2. **Class-Level Cache**

The cache is stored at the class level, not instance level:

```python
class BaseCrawler:
    # Shared across ALL instances of the same crawler class
    _cache_data: Optional[CrawlerResult] = None
    _cache_ts: Optional[datetime] = None
```

This means:
- Creating a new `BonbastCrawler()` instance will reuse the same cache
- Cache persists across multiple job executions
- Only one network request per TTL period, regardless of how many instances are created

### 3. **HTML Parsing Strategy**

Each crawler uses BeautifulSoup to parse HTML:

**BonbastCrawler:**
- Searches for tables with currency names
- Looks for "USD", "EUR", "Gold Gram" in first column
- Extracts sell price from second or third column

**AlanChandCrawler:**
- Searches for tables with currency names (Persian or English)
- Looks for "دلار آمریکا" (USD), "یورو" (EUR), "گرم طلای 18 عیار" (Gold)
- Handles both Persian and English text

**Price Parsing:**
- Removes commas, spaces, Persian comma (،)
- Converts Persian digits (۰-۹) to English (0-9)
- Extracts first number found using regex

### 4. **Error Handling**

- **Network errors**: Caught and logged, doesn't crash the bot
- **Parsing errors**: If price not found, returns `None` for that field
- **Timeout protection**: 10-second timeout prevents hanging
- **Missing prices**: Logged as warnings, doesn't stop execution

## Configuration

All settings are in `.env` file:

```bash
# Crawler URLs
CRAWLER1_URL=https://www.bonbast.com/
CRAWLER2_URL=https://alanchand.com/

# Crawler intervals (in minutes)
CRAWLER1_INTERVAL_MINUTES=37
CRAWLER2_INTERVAL_MINUTES=43

# HTTP timeout (shared with other providers)
HTTP_TIMEOUT_SECONDS=10
```

## Example Execution Flow

**Time: 10:00:00**
1. `crawler1_job()` is triggered (scheduled job)
2. Creates `BonbastCrawler()` instance
3. Calls `crawler.fetch()`
4. Cache check: `_cache_data` is `None` → Cache invalid
5. Fetches HTML from `https://www.bonbast.com/`
6. Parses HTML, finds: USD=107300, EUR=123700, GoldGram=10498
7. Updates cache with result and timestamp
8. Returns `CrawlerResult(usd_sell=107300, eur_sell=123700, gold_gram_sell=10498)`
9. Logs: "Crawler1 (Bonbast) fetched: USD=107300, EUR=123700, GoldGram=10498"

**Time: 10:15:00** (manual trigger or restart)
1. `crawler1_job()` is triggered again
2. Creates new `BonbastCrawler()` instance
3. Calls `crawler.fetch()`
4. Cache check: `_cache_data` exists and only 15 minutes old → Cache valid (37 min TTL)
5. **Returns cached data** (no network request!)
6. Logs: "Using cached crawler data for https://www.bonbast.com/"

**Time: 10:37:00** (next scheduled run)
1. `crawler1_job()` is triggered
2. Creates `BonbastCrawler()` instance
3. Calls `crawler.fetch()`
4. Cache check: `_cache_data` exists but 37 minutes old → Cache expired
5. Fetches fresh HTML from website
6. Parses and updates cache
7. Returns new prices

## Summary

The logic ensures:
- ✅ **Efficient**: Only fetches when cache expires
- ✅ **Safe**: Prevents rate limiting and bans
- ✅ **Resilient**: Handles errors gracefully
- ✅ **Configurable**: URLs and intervals from `.env`
- ✅ **Logged**: All operations are logged for debugging

