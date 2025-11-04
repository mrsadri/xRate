# Data Sources Documentation

## Data Source Overview

The XRate bot uses **web crawlers as primary data sources** with API fallback mechanisms:

1. **Web Crawlers** (Primary Sources)
   - **Bonbast.com** (Crawler1)
   - **AlanChand.com** (Crawler2)
2. **API Providers** (Fallback Sources)
   - **Navasan** (Fallback when crawlers fail)
   - **Wallex** (Tether data, standalone)
3. **Avalai** (Optional AI Analysis)

**Priority Order**: Crawlers (Bonbast → AlanChand) → Navasan API

---

## 1. Web Crawlers (Primary Data Sources)

### 1.1 Bonbast.com (Crawler1)

**Purpose**: Primary source for USD, EUR, and GoldGram sell prices

**URL**: https://www.bonbast.com/ (configurable via `CRAWLER1_URL`)

**Key Required**: No (public website)

**Provides**:
- USD sell price in Toman
- EUR sell price in Toman
- GoldGram (18K) sell price in Toman

**Scheduling**: Runs every 37 minutes by default (configurable via `CRAWLER1_INTERVAL_MINUTES`)

**Caching**: Built-in TTL-based caching at class level to prevent rate limiting and IP bans

**Fallback Strategy**: If Bonbast fails, tries AlanChand, then Navasan API

**Implementation**: See [CRAWLER_LOGIC.md](CRAWLER_LOGIC.md) for detailed implementation

---

### 1.2 AlanChand.com (Crawler2)

**Purpose**: Fallback crawler for USD, EUR, and GoldGram sell prices

**URL**: https://alanchand.com/ (configurable via `CRAWLER2_URL`)

**Key Required**: No (public website)

**Provides**:
- USD sell price in Toman
- EUR sell price in Toman
- GoldGram (18K) sell price in Toman

**Scheduling**: Runs every 43 minutes by default (configurable via `CRAWLER2_INTERVAL_MINUTES`)

**Caching**: Built-in TTL-based caching at class level to prevent rate limiting and IP bans

**Fallback Strategy**: Used when Bonbast fails, then falls back to Navasan API if both crawlers fail

**Implementation**: See [CRAWLER_LOGIC.md](CRAWLER_LOGIC.md) for detailed implementation

---

## 2. API Providers (Fallback Sources)

### 2.1 Navasan (Fallback Provider)

**Purpose**: Fallback for Iranian market data (USD/EUR/Gold in Toman) when both crawlers fail

**URL**: http://api.navasan.tech/latest/

**Key Required**: Yes (optional, but recommended for fallback) - Get from [Navasan.tech](http://api.navasan.tech/)

**Provides**:
- USD price in Toman
- EUR price in Toman
- 18K Gold price per gram in Toman

**Usage**: Only used when both Bonbast and AlanChand crawlers fail

**Cache**: Configurable via `NAVASAN_CACHE_MINUTES` (default: 28 minutes, can be up to 1440)

**API Key Format**: Included in URL as query parameter `?api_key=YOUR_KEY`

---

### 2.2 Wallex (Standalone Provider)

**Purpose**: Tether (USDT-TMN) market data including price and 24-hour change percentage

**URL**: https://api.wallex.ir/v1/markets

**Key Required**: No (public API)

**Provides**:
- Tether (USDT-TMN) current price in Toman
- 24-hour change percentage

**Usage**: Checked separately for Tether market data (optional feature)

**Standalone**: No fallback (optional feature)

**Cache**: Configurable via `WALLEX_CACHE_MINUTES` (default: 15 minutes)

---

## 3. Avalai API (AI Market Analysis)

**Purpose**: Optional AI-powered market analysis in Farsi

**URL**: https://api.avalai.ir/v1

**Key Required**: Yes (optional) - Get from [Avalai.ir](https://avalai.ir)

**Provides**:
- AI-generated market analysis in Persian/Farsi
- Market commentary and insights

**Usage**: Optional - only used if `AVALAI_KEY` is configured

**Cache**: No caching (generated on-demand)

**Integration**: Non-blocking - failures never affect main posting functionality

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Market Data Request                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Try Crawler1 (Bonbast)                            │
│  - Check cache validity                                    │
│  - If cache expired, fetch fresh HTML                      │
│  - Parse USD, EUR, GoldGram prices                         │
│  - Return if all prices found                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
               SUCCESS          FAILURE
                    │             │
                    ▼             ▼
         Return snapshot    ┌─────────────────────────────────┐
                            │ Step 2: Try Crawler2 (AlanChand)│
                            │ - Check cache validity          │
                            │ - If cache expired, fetch HTML  │
                            │ - Parse USD, EUR, GoldGram      │
                            │ - Return if all prices found    │
                            └──────────────────┬──────────────┘
                                               │
                                        ┌──────┴──────┐
                                        │             │
                                   SUCCESS          FAILURE
                                        │             │
                                        ▼             ▼
                             Return snapshot    ┌─────────────────────┐
                                                │ Step 3: Navasan API │
                                                │ - Fallback to API   │
                                                │ - Return if available│
                                                └─────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Crawler Settings
CRAWLER1_URL=https://www.bonbast.com/
CRAWLER1_INTERVAL_MINUTES=37
CRAWLER2_URL=https://alanchand.com/
CRAWLER2_INTERVAL_MINUTES=43

# API Keys (for fallback)
NAVASAN_API_KEY=your_navasan_key  # Optional
AVALAI_KEY=your_avalai_key  # Optional

# Cache Settings
NAVASAN_CACHE_MINUTES=28
WALLEX_CACHE_MINUTES=15
```

---

## Provider Names in Persian

Provider names are translated to Persian in messages:
- **Wallex** → ولکس
- **AlanChand** → الان‌چند
- **Bonbast** → بن‌بست
- **Navasan** → نوسان

---

## Health Monitoring

All data sources are monitored via the `/health` command:
- **Crawlers**: Status, last usage times, and fetched prices
- **Navasan**: API availability and response time
- **Wallex**: API availability
- **Avalai**: Wallet credit and API availability

---

## Error Handling

- **Crawler Failures**: Automatic fallback to next crawler or Navasan API
- **API Failures**: Graceful degradation with error logging
- **Network Issues**: Retry logic with timeouts
- **Data Validation**: Strict validation of fetched prices before use

---

## See Also

- [CRAWLER_LOGIC.md](CRAWLER_LOGIC.md) - Detailed crawler implementation
- [README.md](../README.md) - Main project documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
