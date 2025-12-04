# XRate — Advanced Telegram Exchange Rate Bot

A production-ready Telegram bot that monitors **Iranian market data** (USD/EUR/Gold in Toman) with intelligent posting, health monitoring, and comprehensive error handling. Uses web crawlers as primary data source with API fallback.

Built with **Clean Architecture** principles.

---

## 📑 **Table of Contents**

1. [Quick Start](#-quick-start)
2. [Features](#-key-features)
3. [Configuration](#-configuration)
4. [Bot Commands](#-bot-commands)
5. [Project Structure](#-project-structure)
6. [Architecture](#-architecture)
7. [Testing](#-testing)
8. [Deployment](#-deployment)
9. [Development](#-development)
10. [Documentation](#-documentation)

---

## ⚙️ **Quick Start**

### **Prerequisites**
- Python 3.9+ (3.12+ recommended)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- API Keys: Navasan (optional, for fallback), Avalai (optional, for AI analysis)

### **Installation**
```bash
git clone https://github.com/mrsadri/xRate.git
cd xrate
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install -e .
cp .env.example .env  # Edit with your API keys
python -m xrate
```

### **Data Sources**
- **Web Crawlers** (Primary): Fetch prices directly from websites
  - **Bonbast.com** (Crawler1): USD, EUR, GoldGram sell prices every 37 minutes (configurable)
  - **AlanChand.com** (Crawler2): USD, EUR, GoldGram sell prices every 43 minutes (configurable)
- **API Providers** (Fallback): When crawlers are unavailable
  - **Navasan**: Iranian market data → [Get Key](http://api.navasan.tech)
  - **Wallex**: Tether/USDT-TMN data (no key required)
- **Avalai** (Optional): AI market analysis → [Get Key](https://avalai.ir)

**Priority Order:** Crawlers (Bonbast → AlanChand) → Navasan API (for Iranian market data)

**See [API_PROVIDERS.md](docs/API_PROVIDERS.md) for detailed provider information.**
**See [CRAWLER_LOGIC.md](docs/CRAWLER_LOGIC.md) for crawler implementation details.**

---

## 🚀 **Key Features**

### **Core Functionality**
- 🔁 **Smart Posting**: Posts market updates based on consolidated percentage thresholds (currency upper/lower, gold upper/lower)
- 💬 **Admin Commands**: `/irr`, `/health`, `/post`, `/posttest`, `/language` (admin-only)
- 🕷️ **Web Crawlers**: Direct price fetching from Bonbast and AlanChand websites with TTL-based caching
- 🌍 **Multi-Source Fallback**: Crawlers (Bonbast → AlanChand) → Navasan API with provider attribution
- 📊 **Change Tracking**: Shows percentage changes and elapsed time in Persian format
- 🌐 **Multi-language**: English and Farsi (فارسی) support (default: Persian)
- 📈 **Statistics**: Activity tracking with daily summaries including crawler usage times and user feedback
- 🤖 **AI Analysis**: Optional Farsi market analysis via Avalai API
- ⏰ **Daily Morning Posts**: Automatic 8:00 AM posts (excluding Thursday and Friday)
- 📝 **User Feedback**: Non-admin messages stored as feedback and included in daily reports

### **Enterprise Features**
- 🛡️ **Security**: Input validation, namespaced rate limiting, configuration validation
- 🔍 **Health Monitoring**: Real-time system health checks and API status
- 🧪 **Testing**: 100+ test cases with pytest
- 📈 **Observability**: Structured logging, error tracking, monitoring
- 🏗️ **Clean Architecture**: Layered architecture with dependency inversion
- 🔄 **Reliability**: TTL-based caching, state persistence, graceful error handling

---

## 🔧 **Configuration**

### **Required Environment Variables**
```bash
# Telegram
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@yourchannel
ADMIN_USERNAME=YourUsername

# API Keys
NAVASAN_API_KEY=your_navasan_key  # Optional, for fallback when crawlers fail
AVALAI_KEY=your_avalai_key  # Optional, for AI analysis

# Channel Settings
TEST_CHANNEL_ID=@yourtestchannel  # Optional, for test channel

# Cache Settings (minutes)
NAVASAN_CACHE_MINUTES=28
WALLEX_CACHE_MINUTES=15

# Crawler Settings (Web scrapers for price data)
CRAWLER1_URL=https://www.bonbast.com/
CRAWLER1_INTERVAL_MINUTES=37
CRAWLER2_URL=https://alanchand.com/
CRAWLER2_INTERVAL_MINUTES=43

# Thresholds (% vs last announced) - Consolidated thresholds
MARGIN_CURRENCY_UPPER_PCT=1.0   # Currency (USD/EUR) price increase threshold
MARGIN_CURRENCY_LOWER_PCT=2.0   # Currency (USD/EUR) price decrease threshold
MARGIN_GOLD_UPPER_PCT=1.0       # Gold price increase threshold
MARGIN_GOLD_LOWER_PCT=2.0       # Gold price decrease threshold

# Language Settings
DEFAULT_LANGUAGE=fa  # fa = Persian, en = English

# HTTP Settings
HTTP_TIMEOUT_SECONDS=10

# Persistence
LAST_STATE_FILE=./data/last_state.json
```

**Post interval is automatically calculated as `min(all cache TTLs)` to prevent unnecessary API calls.**

**See [.env.example](.env.example) for complete configuration template.**

---

## 🤖 **Bot Commands**

All commands are **admin-only** (configured via `ADMIN_USERNAME`). Non-admin users can send messages which will be stored as feedback and included in daily reports.

| Command | Description | Access | Rate Limit |
|---------|-------------|--------|------------|
| `/irr` | Get Iranian market snapshot (USD/EUR/Gold) in Persian format | Admin | 30/min |
| `/health` | Check system health (crawlers, APIs, Avalai wallet) | Admin | 5/min |
| `/post` | Manually post market update to main channel | Admin | 30/min |
| `/posttest` | Manually post market update to test channel | Admin | 30/min |
| `/language` | Change bot language (English/Farsi) | Admin | 30/min |
| Any text message | Admin: Shows market data<br>Non-admin: Stores as feedback | All | 10/min |

**See [COMMANDS.md](docs/COMMANDS.md) for detailed command documentation and examples.**

---

## 🗂️ **Project Structure**

```
xrate/
├── src/xrate/              # Main package
│   ├── domain/             # Pure business logic (models, errors)
│   ├── application/        # Use cases (rates_service, state_manager, stats, health)
│   ├── adapters/           # External integrations
│   │   ├── providers/      # API clients (Navasan, Wallex)
│   │   ├── crawlers/       # Web crawlers (Bonbast, AlanChand)
│   │   ├── telegram/       # Bot handlers and jobs
│   │   ├── formatting/     # Message formatting
│   │   ├── persistence/   # File storage
│   │   └── ai/             # Avalai API client
│   ├── config/             # Configuration management
│   └── shared/             # Utilities (rate_limiter, validators, language)
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── deploy/                 # Deployment files (systemd, supervisor)
└── docs/                   # Additional documentation
```

---

## 🏗️ **Architecture**

XRate follows **Clean Architecture** with four layers:

1. **Domain Layer**: Pure business logic, no external dependencies
2. **Application Layer**: Use cases and business logic orchestration
3. **Adapters Layer**: External integrations (APIs, Telegram, persistence)
4. **Shared Layer**: Cross-cutting concerns (logging, rate limiting, validation)

**See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation, design patterns, and system diagrams.**

---

## 🧪 **Testing**

```bash
# Run all tests
make test
# Or: pytest

# Run with coverage
make test-cov

# Run specific test suites
pytest tests/test_providers.py
pytest tests/test_rates_service.py
```

**Test Coverage:** Providers, Services, Formatters, Error Handling

---

## 🚀 **Deployment**

### **Local Development**
```bash
make run
# Or: python -m xrate
```

### **Production Server**
```bash
# Automated deployment
sudo ./deploy/deploy.sh systemd  # or supervisor

# Manual setup
sudo systemctl start xrate
sudo systemctl status xrate
```

**See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.**

---

## 🚧 **Development**

```bash
make install    # Install dependencies
make run        # Run bot
make test       # Run tests
make lint       # Run linting
make fmt        # Format code
make check      # Run all checks
```

**See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.**

---

## 📚 **Documentation**

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment instructions
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[deploy/SERVER_DEPLOYMENT.md](deploy/SERVER_DEPLOYMENT.md)** - Server deployment details
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architecture details
- **[docs/API_PROVIDERS.md](docs/API_PROVIDERS.md)** - API provider details
- **[docs/CRAWLER_LOGIC.md](docs/CRAWLER_LOGIC.md)** - Web crawler implementation and logic

---

## 📦 **Dependencies**

| Package | Version | Purpose |
|---------|---------|---------|
| python-telegram-bot[job-queue] | 21.6 | Telegram bot API |
| requests | 2.32.3 | HTTP client |
| beautifulsoup4 | ≥4.12.0 | HTML parsing for web crawlers |
| python-dotenv | 1.0.1 | Environment variables |
| pydantic | ≥2.0.0 | Data validation |
| pydantic-settings | ≥2.0.0 | Settings management |

---

## 🔍 **Monitoring & Health Checks**

- **Health Monitoring**: Crawlers (Bonbast, AlanChand), Navasan, Wallex, Avalai Wallet, State Manager, Data Pipeline
- **Logging**: Structured logging with file rotation (optional)
- **Rate Limiting**: Per-user limits with namespaced buckets (public/admin/health)
- **Error Tracking**: Comprehensive exception handling with detailed logging
- **Crawler Caching**: Built-in TTL-based caching prevents rate limiting and IP bans

---

## 🔒 **Security Features**

- Input validation for bot tokens, channel IDs, API keys
- Namespaced rate limiting (prevents cross-type interference)
- Configuration validation using Pydantic
- Secure error messages (no sensitive data exposure)

---

## 🐛 **Troubleshooting**

**Bot not responding:**
```bash
tail -f bot.log  # Check logs
python -c "from xrate.config import settings; settings.validate()"  # Verify config
```

**Rate limit exceeded:** Wait 5 minutes for reset

**API errors:** Verify API keys are correct and active

---

## 📄 **License**

MIT License © 2025 **Masih Sadri**

[github.com/mrsadri](https://github.com/mrsadri)

---

## 🙏 **Acknowledgments**

- **Bonbast.com** (bonbast.com) for web-crawled market data
- **AlanChand.com** (alanchand.com) for web-crawled market data
- **Navasan.tech** for Iranian market fallback
- **Wallex.ir** for Tether market data
- **python-telegram-bot** team for the excellent framework
- **pytest** team for the testing framework

---

*Last updated: November 2025*  
*Current version: 1.1.0*  
*See [CHANGELOG.md](CHANGELOG.md) for version history*
