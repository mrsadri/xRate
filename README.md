# XRate — Advanced Telegram Exchange Rate Bot

A production-ready, enterprise-grade Telegram bot that monitors **EUR→USD exchange rates** and **Iranian market data** (USD/EUR/Gold in Toman) with intelligent posting, health monitoring, and comprehensive error handling.

Built with **Clean Architecture** principles, featuring clear separation of concerns, dependency inversion, and comprehensive test coverage.

---

## 🚀 **Key Features**

### **Core Functionality**
* 🔁 **Smart Posting**: Posts market updates based on configurable percentage thresholds
* 💬 **Interactive Commands**: `/start`, `/irr`, `/health`, `/post`, `/language` commands with rate limiting
* 🌍 **Multi-Provider Market Data**: 
  - EUR→USD rates (BRS API → FastForex fallback)
  - Iranian market: USD/EUR/Gold in Toman (BRS API → Navasan fallback)
  - Tether (USDT-TMN) from Wallex API (standalone)
* 📊 **Change Tracking**: Shows percentage changes and elapsed time since last update
* 🔄 **Provider Tracking**: Displays which data providers contributed to each message
* 🌐 **Multi-language**: Support for English and Farsi (فارسی) with admin-controlled switching
* 📈 **Statistics Tracking**: Comprehensive activity tracking with daily summaries
* 🔔 **Admin Notifications**: Startup notifications and daily reports sent to admin
* 🤖 **AI-Powered Market Analysis**: Automatic generation of one-line market analysis in Farsi using Avalai API, considering recent news in Iran

### **Enterprise Features**
* 🛡️ **Security**: Input validation, rate limiting, configuration validation
* 🔍 **Health Monitoring**: Real-time system health checks and API monitoring
* 🧪 **Comprehensive Testing**: 100+ test cases with pytest
* 📈 **Observability**: Enhanced logging, error tracking, and monitoring
* 🏗️ **Clean Architecture**: Layered architecture with domain, application, adapters, and shared layers
* 📦 **Modern Tooling**: pyproject.toml, Makefile, pre-commit hooks, CI/CD

### **Reliability**
* ⚡ **Caching**: Intelligent TTL-based caching to reduce API calls
* 🔄 **State Management**: Centralized state with persistence
* 🚨 **Error Handling**: Comprehensive error handling with specific exception types
* 🔧 **Configuration**: Robust configuration validation and management
* 🔒 **Instance Locking**: Prevents multiple bot instances from running simultaneously
* 🔄 **Auto-restart**: Process manager integration for automatic restart on failure
* 📊 **Production Ready**: Full server deployment support with systemd/Supervisor

---

## 🗂️ **Project Structure**

```
xrate/
├── src/
│   └── xrate/                        # Main package
│       ├── __init__.py              # Package metadata
│       ├── __main__.py              # Entry point (python -m xrate)
│       ├── app.py                   # Application composition root
│       │
│       ├── domain/                  # Domain Layer (Pure Business Logic)
│       │   ├── __init__.py
│       │   ├── models.py            # Domain models (IrrSnapshot, MarketState, etc.)
│       │   └── errors.py            # Domain-specific exceptions
│       │
│       ├── application/             # Application Layer (Use Cases)
│       │   ├── __init__.py
│       │   ├── rates_service.py     # Rate conversion business logic
│       │   ├── state_manager.py     # State management
│       │   ├── stats.py             # Statistics tracking
│       │   └── health.py            # Health monitoring
│       │
│       ├── adapters/                 # Adapters Layer (External Integrations)
│       │   ├── __init__.py
│       │   │
│       │   ├── providers/           # External API providers
│       │   │   ├── __init__.py
│       │   │   ├── base.py          # Provider interface/protocol
│       │   │   ├── brsapi.py         # BRS API client (Primary)
│       │   │   ├── fastforex.py      # FastForex API client (Fallback)
│       │   │   ├── navasan.py        # Navasan API client (Fallback)
│       │   │   └── wallex.py         # Wallex API client (Tether)
│       │   │
│       │   ├── telegram/            # Telegram bot adapters
│       │   │   ├── __init__.py
│       │   │   ├── bot.py           # Bot application builder
│       │   │   ├── handlers.py      # Command handlers
│       │   │   └── jobs.py          # Scheduled jobs
│       │   │
│       │   ├── formatting/         # Message formatting
│       │   │   ├── __init__.py
│       │   │   └── formatter.py    # Text formatting utilities
│       │   │
│       │   ├── persistence/         # Data persistence
│       │   │   ├── __init__.py
│       │   │   ├── file_store.py    # JSON file storage
│       │   │   └── admin_store.py   # Admin ID storage
│       │   │
│       │   ├── ai/                  # AI Service integrations
│       │   │   ├── __init__.py
│       │   │   └── avalai.py       # Avalai API client (market analysis)
│       │   │
│       ├── config/                   # Configuration
│       │   ├── __init__.py
│       │   └── settings.py          # Pydantic-based settings
│       │
│       └── shared/                   # Shared Utilities
│           ├── __init__.py
│           ├── validators.py        # Input validation
│           ├── rate_limiter.py      # Rate limiting
│           ├── language.py          # Multi-language support
│           └── logging_conf.py     # Logging configuration
│
├── tests/                            # Test Suite
│   ├── test_providers.py            # Provider tests
│   ├── test_rates_service.py        # Service layer tests
│   ├── test_formatter.py            # Formatter tests
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── e2e/                          # End-to-end tests
│
├── scripts/                          # Utility scripts
│   ├── run.sh                       # Bot launcher
│   ├── diag.sh                      # Diagnostic script
│   └── add_file_paths.py            # Development utilities
│
├── ci/                               # CI/CD
│   └── github/
│       └── workflows/
│           └── python.yml           # GitHub Actions workflow
│
├── deploy/                           # Deployment files
│   ├── xrate.service                # systemd service file
│   ├── supervisor-xrate.conf       # Supervisor configuration
│   ├── deploy.sh                    # Automated deployment script
│   ├── SERVER_DEPLOYMENT.md         # Server deployment guide
│   └── README.md                    # Deployment overview
│
├── docs/                             # Documentation
├── data/                             # Persistent data
│   ├── last_state.json              # Market state
│   ├── stats.json                   # Statistics
│   └── admin_store.json             # Admin ID
│
├── pyproject.toml                    # Project metadata & dependencies
├── Makefile                         # Common commands
├── .pre-commit-config.yaml          # Pre-commit hooks
├── .env.example                     # Configuration template
├── pytest.ini                       # Test configuration
└── README.md                        # This file
```

---

## ⚙️ **Quick Setup**

### **Prerequisites**
- Python 3.9+ (Python 3.12+ recommended)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Avalai API Key (optional, for market analysis feature) - Get from [avalai.ir](https://avalai.ir)

### **API Providers**

The bot uses **4 providers** with intelligent fallback mechanisms:

1. **BRS API** (Primary Provider)
   - **Purpose**: Primary source for EUR/USD rates and Iranian market data (USD, EUR, 18K Gold in Toman)
   - **URL**: https://brsapi.ir/Api/Market/Gold_Currency.php
   - **Key Required**: Yes - Get from [brsapi.ir](https://brsapi.ir)
   - **Fallback**: FastForex (for EUR/USD) and Navasan (for Iranian market)

2. **FastForex** (Fallback Provider)
   - **Purpose**: Fallback for EUR/USD exchange rates when BRS API fails
   - **URL**: https://api.fastforex.io/
   - **Key Required**: Yes - Get from [FastForex.io Console](https://console.fastforex.io/api-keys/listing)
   - **Used For**: EUR/USD rate only

3. **Navasan** (Fallback Provider)
   - **Purpose**: Fallback for Iranian market data (USD/EUR/Gold in Toman) when BRS API fails
   - **URL**: http://api.navasan.tech/latest/
   - **Key Required**: Yes - Get from [Navasan.tech](http://api.navasan.tech/)
   - **Used For**: USD, EUR, and Gold prices in Toman

4. **Wallex** (Standalone Provider)
   - **Purpose**: Tether (USDT-TMN) market data including price and 24-hour change percentage
   - **URL**: https://api.wallex.ir/v1/markets
   - **Key Required**: No (public API)
   - **Used For**: Tether price and 24h change percentage
   - **Standalone**: No fallback (optional feature)

### **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/masihsadri/xrate.git
   cd xrate
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   # Or with development dependencies:
   pip install -e ".[dev]"
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Run the bot**
   ```bash
   # Using Make
   make run
   
   # Or using script
   ./scripts/run.sh
   
   # Or directly
   python -m xrate
   ```

---

## 🔧 **Configuration**

### **Required Environment Variables**

See `.env.example` for complete configuration. Key settings:

```bash
# Telegram Configuration
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@yourchannel
ADMIN_USERNAME=YourUsername

# API Keys (All Providers)
# FastForex: https://console.fastforex.io/api-keys/listing
FASTFOREX_KEY=your_fastforex_api_key
# Navasan: http://api.navasan.tech/latest/?api_key=YOUR_KEY
NAVASAN_API_KEY=your_navasan_api_key
# BRS API: https://brsapi.ir/Api/Market/Gold_Currency.php?key=YOUR_KEY
BRSAPI_KEY=your_brsapi_key
# Wallex API: No token required (public API for Tether/USDT-TMN)

# HTTP Settings (in seconds)
HTTP_TIMEOUT_SECONDS=10

# Cache Settings (in minutes)
# Note: Post interval is automatically calculated as the minimum of all cache TTLs
FASTFOREX_CACHE_MINUTES=15    # FastForex API cache TTL
NAVASAN_CACHE_MINUTES=28      # Navasan API cache TTL
BRSAPI_CACHE_MINUTES=15       # BRS API cache TTL
WALLEX_CACHE_MINUTES=15        # Wallex API cache TTL

# Announcement Thresholds (% vs last announced)
MARGIN_USD_UPPER_PCT=1.0      # USD price increase threshold
MARGIN_USD_LOWER_PCT=2.0      # USD price decrease threshold
MARGIN_EUR_UPPER_PCT=1.0      # EUR price increase threshold
MARGIN_EUR_LOWER_PCT=2.0      # EUR price decrease threshold
MARGIN_GOLD_UPPER_PCT=1.0     # Gold price increase threshold
MARGIN_GOLD_LOWER_PCT=2.0     # Gold price decrease threshold
MARGIN_EURUSD_UPPER_PCT=1.0   # EUR/USD rate increase threshold
MARGIN_EURUSD_LOWER_PCT=2.0   # EUR/USD rate decrease threshold
MARGIN_TETHER_UPPER_PCT=1.0   # Tether 24h change increase threshold
MARGIN_TETHER_LOWER_PCT=2.0   # Tether 24h change decrease threshold

# Avalai API (for market analysis)
# Optional: Leave empty to disable AI analysis feature
AVALAI_KEY=your_avalai_api_key

# Persistence
LAST_STATE_FILE=./data/last_state.json

# Logging Configuration (optional, for server deployment)
# LOG_DIR=/opt/xrate/logs          # Directory for log files
# LOG_FILE=/var/log/xrate/bot.log  # Specific log file path
# XRATE_LOG_STDOUT=true             # Enable/disable stdout logging (default: true)
# LOG_MAX_BYTES=10485760            # Max log file size before rotation (default: 10MB)
# LOG_BACKUP_COUNT=5                # Number of backup log files (default: 5)
```

### **Provider Configuration Details**

#### **BRS API (Primary Provider)**
- **Status**: Primary provider for all market data
- **Required**: Yes (but can work with FastForex + Navasan as fallbacks)
- **Provides**:
  - EUR/USD exchange rate
  - USD price in Toman
  - EUR price in Toman
  - 18K Gold price per gram in Toman
- **Fallback Strategy**: If BRS fails, uses FastForex for EUR/USD and Navasan for Iranian market data
- **Cache**: Configurable via `BRSAPI_CACHE_MINUTES` (default: 15 minutes)

#### **FastForex (Fallback Provider)**
- **Status**: Fallback for EUR/USD rates only
- **Required**: Yes (for EUR/USD fallback)
- **Provides**: EUR/USD exchange rate
- **Usage**: Only used when BRS API fails for EUR/USD rate
- **Cache**: Configurable via `FASTFOREX_CACHE_MINUTES` (default: 15 minutes)
- **Get API Key**: [FastForex Console](https://console.fastforex.io/api-keys/listing)

#### **Navasan (Fallback Provider)**
- **Status**: Fallback for Iranian market data
- **Required**: Yes (for Iranian market fallback)
- **Provides**:
  - USD price in Toman
  - EUR price in Toman
  - 18K Gold price per gram in Toman
- **Usage**: Only used when BRS API fails for Iranian market data
- **Cache**: Configurable via `NAVASAN_CACHE_MINUTES` (default: 28 minutes, can be up to 1440)
- **Get API Key**: [Navasan API](http://api.navasan.tech/)

#### **Wallex (Tether Provider)**
- **Status**: Standalone provider for Tether data
- **Required**: No (optional feature)
- **Provides**:
  - Tether (USDT-TMN) current price in Toman
  - 24-hour change percentage
- **Usage**: Checked separately for Tether market data; added to messages when threshold is breached
- **API Key**: Not required (public API)
- **Cache**: Configurable via `WALLEX_CACHE_MINUTES` (default: 15 minutes)
- **API**: https://api.wallex.ir/v1/markets

#### **Avalai API (Market Analysis)**
- **Status**: Optional AI-powered market analysis
- **Required**: No (optional feature)
- **Purpose**: Generates one-line market analysis in Farsi based on price data and recent news in Iran
- **How It Works**:
  1. After each price update is posted to the channel
  2. The bot sends the price message to Avalai API with context about recent Iran news
  3. Avalai generates a contextual one-line analysis in Farsi
  4. The analysis is automatically sent as a separate message to the channel
- **API Key**: Required if you want to enable this feature - Get from [avalai.ir](https://avalai.ir)
- **Model**: Uses GPT-5 model via Avalai API
- **API Base URL**: https://api.avalai.ir/v1
- **Example Output**: "بر اساس کاهش قیمت دلار و یورو، احتمالاً فشارهای سیاسی بر بازار ارز تاثیرگذار بوده است."
- **Configuration**: 
  - Set `AVALAI_KEY` in `.env` file to enable the feature
  - Leave empty or omit to disable (bot continues working normally)
  - Feature gracefully handles API failures without affecting main posting functionality

### **Automatic Post Interval Calculation**

The bot **automatically calculates** the posting interval as the **minimum** of all cache TTLs:

```
Post Interval = min(
  FASTFOREX_CACHE_MINUTES,
  NAVASAN_CACHE_MINUTES,
  BRSAPI_CACHE_MINUTES,
  WALLEX_CACHE_MINUTES
)
```

This ensures the bot doesn't check more frequently than data is refreshed, preventing unnecessary API calls while ensuring fresh data.

**Example**: If cache settings are `[15, 360, 15, 15]` minutes, the post interval will be **15 minutes** (the minimum).

### **Configuration Validation**
The bot automatically validates:
- Bot token format
- Channel ID format
- API key formats
- Numeric ranges
- Required fields

---

## 🤖 **Bot Commands**

### **Available Commands**

| Command | Description | Access | Rate Limit |
|---------|-------------|--------|------------|
| `/start` | Get current market data with percentage changes | Public | 10/min |
| `/irr` | Get Iranian market snapshot (USD/EUR/Gold) | Public | 10/min |
| `/health` | Check system health and API status | Public | 5/min |
| `/post` | Manually post market update to channel | Admin | 30/min |
| `/language` | Change bot language (English/Farsi) | Admin | 30/min |

### **Example Outputs**

**`/start` Command:**
```
(USD 💵) $1   = 108.4 KToman        2.1% 📈
(Euro 💶) €1  = 126.0 KToman        1.5% 📉
(Gold 🏆) 1gr = 0.011 MToman     0.0% ⏸
(Euro 💶) €1  = $1.1234 (USD 💵)  1.2% 📈
Time spent from previous announcement: 2h:15min
Reported by brsapi and fastforex
```

**Smart Formatting:** The bot only shows market items (USD, EUR, Gold, EUR/USD, Tether) that have breached their thresholds, keeping messages concise and relevant.

**AI Analysis (if Avalai API is configured):**
After the price update, the bot automatically generates and posts a contextual analysis:
```
بر اساس کاهش قیمت دلار و یورو، احتمالاً فشارهای سیاسی بر بازار ارز تاثیرگذار بوده است.
```

The analysis considers:
- Current price movements and trends
- Recent news and events in Iran
- Market context and patterns

**`/health` Command:**
```
✅ System Health Check

All systems healthy

✅ Fastforex: FastForex API healthy, rate: 1.1234
✅ Navasan: Navasan API healthy, 15 data points
✅ State Manager: State manager healthy, last update: 45s ago
✅ Irr Data: IRR data fetch successful

🕐 Checked at: 2025-01-27T10:30:45.123456+00:00
```

---

## 🧪 **Testing**

### **Run Tests**
```bash
# Run all tests
make test
# Or: pytest

# Run with coverage
make test-cov
# Or: pytest --cov=src/xrate --cov-report=html

# Run specific test suites
pytest tests/test_providers.py
pytest tests/test_rates_service.py
pytest tests/test_formatter.py

# Run with verbose output
pytest -v
```

### **Test Coverage**
- **Providers**: BRS API, FastForex, Navasan, and Wallex API clients
- **Services**: Rate conversion and state management
- **Formatters**: Message formatting and utilities
- **Error Handling**: Exception scenarios and edge cases

---

## 🚀 **Development**

### **Common Commands**

```bash
# Install dependencies
make install

# Run the bot
make run

# Run tests
make test

# Run linting
make lint

# Format code
make fmt

# Run all checks (lint, format, test)
make check
```

---

## 🏗️ **Architecture Overview**

The XRate bot follows **Clean Architecture** principles with clear separation of concerns across four layers:

### **Layer Structure**

```
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  Pure business logic, no external dependencies              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Models     │  │    Errors    │  │  Business Rules   │ │
│  │  (Entities)  │  │ (Exceptions) │  │                   │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ (depends on)
┌─────────────────────────────────────────────────────────────┐
│                 Application Layer                            │
│  Use cases and business logic orchestration                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ RatesService │  │StateManager  │  │  HealthChecker    │ │
│  │ StatsTracker │  │              │  │                   │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ (depends on)
┌─────────────────────────────────────────────────────────────┐
│                  Adapters Layer                               │
│  External integrations and infrastructure                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Providers   │  │  Telegram    │  │   Persistence    │ │
│  │  (APIs)      │  │  (Bot)       │  │   (File Store)   │ │
│  │  - BRS       │  │  - Handlers  │  │   - State        │ │
│  │  - FastForex │  │  - Jobs      │  │   - Stats        │ │
│  │  - Navasan   │  │  - Formatting│  │   - Admin        │ │
│  │  - Wallex    │  │              │  │                   │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ (uses)
┌─────────────────────────────────────────────────────────────┐
│                   Shared Layer                                │
│  Cross-cutting concerns and utilities                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Validators  │  │ Rate Limiter │  │   Language       │ │
│  │  Logging     │  │              │  │   Support        │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### **Dependency Flow**

```
Domain Layer (Independent)
    ↑
Application Layer (depends on Domain)
    ↑
Adapters Layer (depends on Application & Domain)
    ↑
Shared Layer (used by all layers)
```

**Key Principles:**
1. **Dependency Inversion**: High-level modules don't depend on low-level modules; both depend on abstractions
2. **Separation of Concerns**: Each layer has a single, well-defined responsibility
3. **Testability**: Business logic is isolated and easily testable
4. **Flexibility**: Easy to swap implementations (e.g., different storage backends)

### **System Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Telegram Bot Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Handlers   │  │  Job Queue   │  │   Rate Limiter           │  │
│  │  (Commands)  │  │  (Scheduler) │  │   (Security Layer)       │  │
│  │  - /start    │  │  - Auto Post │  │   - Per-user limits      │  │
│  │  - /post     │  │  - Startup   │  │   - Admin limits        │  │
│  │  - /health   │  │  - Daily Rpt │  │                          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  │
└─────────┼──────────────────┼──────────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ RatesService │  │ StateManager │  │   HealthChecker          │  │
│  │ (Business)   │  │(Persistence) │  │   (Monitoring)           │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ StatsTracker │  │              │  │                          │  │
│  │ (Analytics)  │  │              │  │                          │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘  │
└─────────┼──────────────────┼──────────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Provider Chain Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Provider Chain: EUR/USD Rate                                │   │
│  │  1. BRS API (Primary) ──┐                                    │   │
│  │  2. FastForex (Fallback)└─► RatesService.eur_usd()          │   │
│  │  Priority: BRS → FastForex                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Provider Chain: Iranian Market (USD/EUR/Gold)               │   │
│  │  1. BRS API (Primary) ──┐                                    │   │
│  │  2. Navasan (Fallback)  └─► get_irr_snapshot()              │   │
│  │  Priority: BRS → Navasan                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Provider: Tether (USDT-TMN)                                │   │
│  │  Wallex API (Standalone) ──┐                                │   │
│  │                            └─► Tether price & 24h_ch         │   │
│  │  No fallback (optional feature)                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      External APIs                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  BRS API (Primary)                                          │   │
│  │  • EUR/USD rate                                             │   │
│  │  • USD/EUR/Gold in Toman                                    │   │
│  │  URL: https://brsapi.ir/Api/Market/Gold_Currency.php        │   │
│  │  Key Required: Yes                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastForex (Fallback)                                        │   │
│  │  • EUR/USD rate only                                         │   │
│  │  URL: https://api.fastforex.io/                              │   │
│  │  Key Required: Yes                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Navasan (Fallback)                                          │   │
│  │  • USD/EUR/Gold in Toman                                    │   │
│  │  URL: http://api.navasan.tech/latest/                       │   │
│  │  Key Required: Yes                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Wallex API (Standalone)                                     │   │
│  │  • Tether (USDT-TMN) price & 24h change                      │   │
│  │  URL: https://api.wallex.ir/v1/markets                       │   │
│  │  Key Required: No (public API)                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### **Data Flow Architecture**

```
User Command/Job Trigger
        │
        ▼
┌───────────────────────┐
│  Telegram Bot         │
│  - Handlers           │
│  - Job Queue          │
│  - Rate Limiter       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Application Layer    │
│  - RatesService       │
│  - StateManager       │
│  - StatsTracker       │
└───────────┬───────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│  Provider Chain (Fallback Strategy)                     │
│                                                         │
│  EUR/USD Rate Chain:                                     │
│    BRS API (Primary) → FastForex (Fallback)             │
│                                                          │
│  Iranian Market Chain (USD/EUR/Gold):                  │
│    BRS API (Primary) → Navasan (Fallback)              │
│                                                          │
│  Tether (USDT-TMN):                                     │
│    Wallex (Standalone, optional, no fallback)           │
│                                                         │
│  Each provider has:                                    │
│  - TTL-based caching (15-28 min)                        │
│  - Error handling & retries                            │
│  - Request timeouts                                    │
└───────────┬─────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────┐
│  External APIs        │
│  - BRS API            │
│  - FastForex API      │
│  - Navasan API        │
│  - Wallex API         │
└───────────┬───────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│  Data Processing                                         │
│  - Rate calculations                                   │
│  - Percentage changes                                  │
│  - Threshold checking                                  │
│  - State updates                                       │
│  - Statistics tracking                                 │
│  - Provider attribution                                │
└───────────┬─────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────┐
│  Formatting           │
│  - Message formatting  │
│  - Emoji & symbols    │
│  - Time formatting    │
│  - Multi-language     │
│  - Smart formatting   │
│    (threshold-based)  │
└───────────┬───────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│  Output Channels                                        │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │  Telegram Channel    │  │  Admin Notifications    │  │
│  │  (Public Posts)      │  │  - Startup messages    │  │
│  │  - Market updates    │  │  - Daily summaries     │  │
│  │  - Provider footer   │  │  - Activity reports    │  │
│  └──────────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### **Component Responsibilities**

**📱 Domain Layer** (`src/xrate/domain/`)
- **Models** (`models.py`): Core business entities (IrrSnapshot, MarketState, etc.)
- **Errors** (`errors.py`): Domain-specific exceptions

**🔧 Application Layer** (`src/xrate/application/`)
- **RatesService** (`rates_service.py`): Core business logic, provider orchestration
- **StateManager** (`state_manager.py`): Manages market state with persistence
- **StatsTracker** (`stats.py`): Tracks bot activity, posts, errors, provider usage
- **HealthChecker** (`health.py`): Monitors system and API health

**🌐 Adapters Layer** (`src/xrate/adapters/`)
- **Providers** (`providers/`): External API integrations (BRS, FastForex, Navasan, Wallex)
- **Telegram** (`telegram/`): Bot handlers, jobs, and messaging
- **Formatting** (`formatting/`): Message formatting and presentation
- **Persistence** (`persistence/`): File-based storage (JSON)

**🔧 Shared Layer** (`src/xrate/shared/`)
- **Validators** (`validators.py`): Input validation and security
- **Rate Limiter** (`rate_limiter.py`): Prevents abuse with per-user rate limiting
- **Language Manager** (`language.py`): Multi-language support
- **Logging** (`logging_conf.py`): Structured logging configuration

### **Key Design Patterns**

1. **Clean Architecture**: Layered architecture with dependency inversion
2. **Provider Chain Pattern**: Sequential fallback (BRS → FastForex/Navasan)
3. **Strategy Pattern**: Interchangeable providers via `RateProvider` protocol
4. **Service Layer Pattern**: Business logic separated from data access
5. **Repository Pattern**: Stats and admin data persistence (JSON-based)
6. **Observer Pattern**: Job queue for scheduled tasks (posting, notifications)
7. **Factory Pattern**: Provider instantiation with configuration
8. **Template Method Pattern**: Message formatting with conditional display
9. **Dependency Injection**: Providers injected into services via constructor

---

## 🚀 **Deployment**

### **Local Development**

1. **Install as package**
   ```bash
   pip install -e .
   ```

2. **Run the bot**
   ```bash
   # Using script
   ./scripts/run.sh
   
   # Or directly
   python -m xrate
   ```

3. **Background Service (Development)**
   ```bash
   nohup ./scripts/run.sh > bot.log 2>&1 &
   
   # Monitor logs
   tail -f bot.log
   
   # Stop service
   pkill -f "python.*xrate"
   ```

### **Production Server Deployment**

The bot is ready for production deployment on Linux servers with **systemd** or **Supervisor** process management.

#### **Quick Start**

1. **Transfer project to server**
   ```bash
   rsync -av --exclude='.git' --exclude='.venv' ./ user@server:/tmp/xrate
   ```

2. **Run automated deployment script**
   ```bash
   ssh user@server
   cd /tmp/xrate
   sudo ./deploy/deploy.sh systemd
   # or for supervisor:
   # sudo ./deploy/deploy.sh supervisor
   ```

3. **Configure environment**
   ```bash
   sudo -u xrate nano /opt/xrate/.env
   # Add your BOT_TOKEN, API keys, etc.
   ```

4. **Start the service**
   ```bash
   # For systemd:
   sudo systemctl start xrate
   
   # For supervisor:
   sudo supervisorctl start xrate
   ```

#### **Service Management**

**Systemd commands:**
```bash
sudo systemctl start xrate      # Start service
sudo systemctl stop xrate       # Stop service
sudo systemctl restart xrate    # Restart service
sudo systemctl status xrate     # Check status
sudo journalctl -u xrate -f     # View logs
```

**Supervisor commands:**
```bash
sudo supervisorctl start xrate      # Start service
sudo supervisorctl stop xrate       # Stop service
sudo supervisorctl restart xrate    # Restart service
sudo supervisorctl status xrate     # Check status
tail -f /opt/xrate/logs/xrate.log  # View logs
```

#### **Server Configuration**

For server deployment, add these optional environment variables to `.env`:

```bash
# Logging Configuration (for servers)
LOG_DIR=/opt/xrate/logs          # Directory for log files
XRATE_LOG_STDOUT=false            # Disable stdout (for systemd/supervisor)
LOG_MAX_BYTES=10485760            # 10MB per log file
LOG_BACKUP_COUNT=5                # Number of backup logs

# Optional: Custom PID file location
XRATE_PID_FILE=/opt/xrate/data/bot.pid
```

**Features:**
- ✅ **File-based logging** with automatic rotation
- ✅ **Process management** via systemd or Supervisor
- ✅ **Auto-restart** on failure
- ✅ **Security hardening** (runs as dedicated user)
- ✅ **Multiple instance prevention** (PID file locking)

#### **Complete Deployment Guide**

For detailed instructions, troubleshooting, and best practices, see:
- **📘 [Complete Deployment Guide](DEPLOYMENT.md)** - Step-by-step guide for beginners
- **📘 [Server Deployment Guide](deploy/SERVER_DEPLOYMENT.md)** - Detailed server deployment instructions

### **Docker Deployment** (Future Enhancement)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY . .
CMD ["python", "-m", "xrate"]
```

---

## 🔍 **Monitoring & Health Checks**

### **Health Monitoring**
- **BRS API**: Primary provider health check (Iranian market + EUR/USD rates)
- **FastForex API**: Fallback provider health check (EUR/USD rates)
- **Navasan API**: Fallback provider health check (Iranian market data)
- **Wallex API**: Tether (USDT-TMN) market data health check
- **State Manager**: State persistence and retrieval
- **Data Fetching**: End-to-end data pipeline validation

### **Logging**
- **Structured Logging**: Consistent log format with timestamps
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **File-based Logging**: Optional file logging with automatic rotation
- **Log Rotation**: Configurable size-based rotation with backup retention
- **Multiple Outputs**: Support for stdout, file, or both simultaneously
- **Server Ready**: Optimized for systemd/supervisor process managers
- **Error Tracking**: Detailed exception information
- **Performance Metrics**: API response times and cache hits

### **Rate Limiting**
- **User Commands**: 10 requests per minute
- **Admin Commands**: 30 requests per minute
- **Health Checks**: 5 requests per minute
- **Automatic Blocking**: 5-minute blocks for excessive usage

---

## 🔒 **Security Features**

### **Input Validation**
- **Bot Token Validation**: Format and structure validation
- **Channel ID Validation**: Telegram channel/chat ID validation
- **API Key Validation**: Length and format validation
- **User Input Sanitization**: XSS and injection prevention

### **Configuration Security**
- **Environment Variables**: Sensitive data in environment variables
- **Validation**: Comprehensive configuration validation using Pydantic
- **Error Handling**: Secure error messages without sensitive data

---

## 📦 **Dependencies**

| Package | Version | Purpose |
|---------|---------|---------|
| **python-telegram-bot[job-queue]** | 21.6 | Telegram bot API |
| **requests** | 2.32.3 | HTTP client for APIs |
| **python-dotenv** | 1.0.1 | Environment variable loading |
| **pydantic** | ≥2.0.0 | Data validation and settings |
| **pydantic-settings** | ≥2.0.0 | Settings management |
| **pytest** | 7.4.3 | Testing framework |
| **pytest-asyncio** | 0.21.1 | Async testing support |
| **pytest-mock** | 3.12.0 | Mocking utilities |

All dependencies are managed via `pyproject.toml`.

---

## 🐛 **Troubleshooting**

### **Common Issues**

**Bot not responding:**
```bash
# Check bot logs
tail -f bot.log

# Verify configuration
python -c "from xrate.config import settings; settings.validate()"

# Test API connectivity
python -c "from xrate.adapters.providers.fastforex import FastForexProvider; print(FastForexProvider().eur_usd_rate())"
```

**Rate limit exceeded:**
- Wait for the rate limit to reset (5 minutes)
- Check if you're using the bot excessively
- Use `/health` command to monitor system status

**API errors:**
- Verify API keys are correct and active
- Check API service status
- Review error logs for specific error messages

---

## 📝 **Contributing**

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Install development dependencies: `pip install -e ".[dev]"`
4. Run pre-commit hooks: `pre-commit install`
5. Run tests before committing: `make test`
6. Submit a pull request

### **Code Standards**
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write comprehensive tests
- Update documentation for new features
- Use pre-commit hooks (Ruff, Black, isort, mypy)

---

## 📄 **License**

MIT License © 2025 **Masih Sadri**

[github.com/masihsadri](https://github.com/masihsadri)

---

## 🙏 **Acknowledgments**

- **BRS API (brsapi.ir)** for primary Iranian market data and exchange rates
- **FastForex.io** for reliable exchange rate data (fallback provider)
- **Navasan.tech** for Iranian market data (fallback provider)
- **Wallex.ir** for Tether (USDT-TMN) market data
- **python-telegram-bot** team for the excellent bot framework
- **pytest** team for the testing framework

---

*Last updated: January 27, 2025*
