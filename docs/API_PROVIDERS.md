# API Providers Documentation

## Provider Overview

The XRate bot uses **4 providers** with intelligent fallback mechanisms:

1. **BRS API** (Primary Provider)
2. **FastForex** (Fallback Provider)
3. **Navasan** (Fallback Provider)
4. **Wallex** (Standalone Provider)

---

## 1. BRS API (Primary Provider)

**Purpose**: Primary source for EUR/USD rates and Iranian market data (USD, EUR, 18K Gold in Toman)

**URL**: https://brsapi.ir/Api/Market/Gold_Currency.php

**Key Required**: Yes - Get from [brsapi.ir](https://brsapi.ir)

**Provides**:
- EUR/USD exchange rate
- USD price in Toman
- EUR price in Toman
- 18K Gold price per gram in Toman

**Fallback Strategy**: If BRS fails, uses FastForex for EUR/USD and Navasan for Iranian market data

**Cache**: Configurable via `BRSAPI_CACHE_MINUTES` (default: 15 minutes)

**API Key Format**: Included in URL as query parameter `?key=YOUR_KEY`

---

## 2. FastForex (Fallback Provider)

**Purpose**: Fallback for EUR/USD exchange rates when BRS API fails

**URL**: https://api.fastforex.io/

**Key Required**: Yes - Get from [FastForex.io Console](https://console.fastforex.io/api-keys/listing)

**Provides**: EUR/USD exchange rate only

**Usage**: Only used when BRS API fails for EUR/USD rate

**Cache**: Configurable via `FASTFOREX_CACHE_MINUTES` (default: 15 minutes)

**API Key Format**: Included in URL as query parameter `?api_key=YOUR_KEY`

---

## 3. Navasan (Fallback Provider)

**Purpose**: Fallback for Iranian market data (USD/EUR/Gold in Toman) when BRS API fails

**URL**: http://api.navasan.tech/latest/

**Key Required**: Yes - Get from [Navasan.tech](http://api.navasan.tech/)

**Provides**:
- USD price in Toman
- EUR price in Toman
- 18K Gold price per gram in Toman

**Usage**: Only used when BRS API fails for Iranian market data

**Cache**: Configurable via `NAVASAN_CACHE_MINUTES` (default: 28 minutes, can be up to 1440)

**API Key Format**: Included in URL as query parameter `?api_key=YOUR_KEY`

---

## 4. Wallex (Standalone Provider)

**Purpose**: Tether (USDT-TMN) market data including price and 24-hour change percentage

**URL**: https://api.wallex.ir/v1/markets

**Key Required**: No (public API)

**Provides**:
- Tether (USDT-TMN) current price in Toman
- 24-hour change percentage

**Usage**: Checked separately for Tether market data; added to messages when threshold is breached

**Standalone**: No fallback (optional feature)

**Cache**: Configurable via `WALLEX_CACHE_MINUTES` (default: 15 minutes)

---

## 5. Avalai API (AI Market Analysis)

**Purpose**: Optional AI-powered market analysis in Farsi

**URL**: https://api.avalai.ir/v1

**Key Required**: Yes (optional) - Get from [avalai.ir](https://avalai.ir)

**Model**: GPT-5 via Avalai API

**How It Works**:
1. After each price update is posted to the channel
2. The bot sends the price message to Avalai API with context about recent Iran news
3. Avalai generates a contextual one-line analysis in Farsi
4. The analysis is automatically sent as a separate message to the channel

**Example Output**: "بر اساس کاهش قیمت دلار و یورو، احتمالاً فشارهای سیاسی بر بازار ارز تاثیرگذار بوده است."

**Configuration**: 
- Set `AVALAI_KEY` in `.env` file to enable the feature
- Leave empty or omit to disable (bot continues working normally)
- Feature gracefully handles API failures without affecting main posting functionality

---

## Provider Chain Flow

### EUR/USD Rate Chain
```
BRS API (Primary) → FastForex (Fallback)
```

### Iranian Market Chain
```
BRS API (Primary) → Navasan (Fallback)
```

### Tether Chain
```
Wallex (Standalone, no fallback)
```

---

## Per-Provider TTL Tracking

The bot tracks each provider's TTL independently to prevent rate limiting:

- **Post Interval**: Automatically calculated as `min(all cache TTLs)`
- **Provider Fetching**: Each provider is only fetched when its individual TTL has elapsed
- **Example**: If Navasan has 28-minute TTL but job runs every 15 minutes, Navasan is only fetched once every 28 minutes

This prevents hitting rate limits on providers with longer cache windows.

---

## Error Handling

All providers include:
- **Timeout Handling**: Configurable HTTP timeouts (default: 10 seconds)
- **Retry Logic**: Automatic fallback to next provider in chain
- **Cache Validation**: TTL-based caching to reduce API calls
- **Graceful Degradation**: Bot continues working even if some providers fail

---

## Rate Limiting

Each provider is tracked independently to respect their individual cache TTLs, preventing:
- 429 (Too Many Requests) errors
- API bans
- Unnecessary API calls

The bot's job scheduler respects per-provider TTL windows even when the global post interval is shorter.

