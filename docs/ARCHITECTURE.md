# Architecture Documentation

## Overview

XRate follows **Clean Architecture** principles with clear separation of concerns, dependency inversion, and comprehensive test coverage.

---

## Layer Structure

The architecture consists of four main layers:

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

### Dependency Flow

```
Domain Layer (Independent)
    ↑
Application Layer (depends on Domain)
    ↑
Adapters Layer (depends on Application & Domain)
    ↑
Shared Layer (used by all layers)
```

---

## Layer Details

### 1. Domain Layer (`src/xrate/domain/`)

**Purpose**: Pure business logic with no external dependencies

**Components**:
- **Models** (`models.py`): Core business entities
  - `IrrSnapshot`: Iranian market data (USD/EUR/Gold in Toman)
  - `MarketState`: Complete market state at a point in time
  - `Rate`: Exchange rate value with timestamp
  - `Change`: Percentage change representation
  - `ProviderAttribution`: Tracks which providers contributed data

- **Errors** (`errors.py`): Domain-specific exceptions
  - Custom exception types for domain errors

**Key Principles**:
- No external dependencies (no HTTP, no file I/O, no databases)
- Immutable data structures (frozen dataclasses)
- Pure business logic only

---

### 2. Application Layer (`src/xrate/application/`)

**Purpose**: Use cases and business logic orchestration

**Components**:
- **RatesService** (`rates_service.py`): Core business logic
  - Provider orchestration (ProviderChain pattern)
  - EUR/USD rate fetching with fallback
  - High-level domain services

- **StateManager** (`state_manager.py`): State management
  - Manages market state with persistence
  - Tracks last posted values for threshold comparison
  - Handles state updates and retrieval

- **StatsTracker** (`stats.py`): Statistics tracking
  - Activity tracking (posts, errors, provider usage)
  - Daily summaries
  - Overall statistics

- **HealthChecker** (`health.py`): Health monitoring
  - System health checks
  - API provider status monitoring
  - Data pipeline validation

**Key Principles**:
- Depends only on Domain layer
- Orchestrates business logic
- Coordinates adapters via dependency injection

---

### 3. Adapters Layer (`src/xrate/adapters/`)

**Purpose**: External integrations and infrastructure

**Sub-layers**:

#### 3.1 Providers (`adapters/providers/`)
- **BRSAPIProvider**: Primary provider for Iranian market and EUR/USD
- **FastForexProvider**: Fallback for EUR/USD rates
- **NavasanProvider**: Fallback for Iranian market data
- **WallexProvider**: Standalone Tether (USDT-TMN) provider
- **Base Protocol**: `RateProvider` interface for type checking

#### 3.2 Telegram (`adapters/telegram/`)
- **bot.py**: Bot application builder
- **handlers.py**: Command handlers (`/start`, `/irr`, `/health`, `/post`, `/language`)
- **jobs.py**: Scheduled jobs (auto-posting, daily summaries, startup notifications)

#### 3.3 Formatting (`adapters/formatting/`)
- **formatter.py**: Message formatting utilities
  - Market data formatting
  - Percentage change calculations
  - Multi-language support integration
  - Time formatting (elapsed time display)

#### 3.4 Persistence (`adapters/persistence/`)
- **file_store.py**: JSON file storage for state
  - Atomic writes with temporary files
  - Graceful corruption handling
  - Schema validation and recovery
- **admin_store.py**: Admin user ID storage

#### 3.5 AI (`adapters/ai/`)
- **avalai.py**: Avalai API client for market analysis
  - Non-blocking integration
  - Optional feature (graceful degradation)

**Key Principles**:
- Implements interfaces defined by Application layer
- Handles all external communication
- Isolated from business logic

---

### 4. Shared Layer (`src/xrate/shared/`)

**Purpose**: Cross-cutting concerns used by all layers

**Components**:
- **validators.py**: Input validation and security
  - Bot token validation
  - Channel ID validation
  - API key format validation

- **rate_limiter.py**: Rate limiting system
  - Per-user rate limiting
  - Namespaced buckets (public/admin/health)
  - Automatic blocking for excessive usage

- **language.py**: Multi-language support
  - English/Farsi switching
  - Translation functions

- **logging_conf.py**: Structured logging configuration
  - File-based logging with rotation
  - Console logging
  - Server deployment optimization

**Key Principles**:
- Utility functions only
- No business logic
- Used across all layers

---

## Design Patterns

### 1. Provider Chain Pattern

Sequential fallback mechanism for data providers:

```
EUR/USD Rate Chain:
  BRS API (Primary) → FastForex (Fallback)

Iranian Market Chain:
  BRS API (Primary) → Navasan (Fallback)

Tether Chain:
  Wallex (Standalone, no fallback)
```

**Implementation**: `ProviderChain` class in `rates_service.py`

### 2. Strategy Pattern

Interchangeable providers via `RateProvider` protocol:

- All providers implement the same interface
- Easy to swap implementations
- Type-safe provider usage

**Implementation**: `RateProvider` protocol in `providers/base.py`

### 3. Service Layer Pattern

Business logic separated from data access:

- `RatesService`: Orchestrates rate fetching
- `StateManager`: Manages state persistence
- Services coordinate adapters, don't know implementation details

### 4. Repository Pattern

Data persistence abstraction:

- `file_store.py`: JSON-based storage
- `admin_store.py`: Admin ID storage
- Abstracts file I/O from business logic

### 5. Dependency Injection

Providers injected via constructor:

- `RatesService` receives `RateProvider` instance
- Easy to mock for testing
- Flexible provider configuration

### 6. Observer Pattern

Job queue for scheduled tasks:

- Telegram's `JobQueue` for scheduling
- Decoupled job execution
- Event-driven architecture

### 7. Template Method Pattern

Message formatting with conditional display:

- `market_lines_with_changes()` uses flags to show/hide items
- Smart formatting based on threshold breaches
- Consistent formatting across commands

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Telegram Bot Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Handlers   │  │  Job Queue   │  │   Rate Limiter           │  │
│  │  (Commands)  │  │  (Scheduler) │  │   (Security Layer)       │  │
│  │  - /start    │  │  - Auto Post │  │   - Per-user limits      │  │
│  │  - /post     │  │  - Startup   │  │   - Admin limits        │  │
│  │  - /health   │  │  - Daily Rpt │  │   - Namespaced buckets  │  │
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
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Provider Chain: Iranian Market (USD/EUR/Gold)               │   │
│  │  1. BRS API (Primary) ──┐                                    │   │
│  │  2. Navasan (Fallback)  └─► get_irr_snapshot()              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Provider: Tether (USDT-TMN)                                │   │
│  │  Wallex API (Standalone) ──┐                                │   │
│  │                            └─► Tether price & 24h_ch         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      External APIs                                  │
│  • BRS API • FastForex • Navasan • Wallex • Avalai                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

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
│  - Per-provider TTL tracking                            │
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
│  - Percentage changes (Decimal-based, with hysteresis) │
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

---

## Component Responsibilities

### 📱 Domain Layer (`src/xrate/domain/`)
- **Models**: Core business entities (IrrSnapshot, MarketState, etc.)
- **Errors**: Domain-specific exceptions

### 🔧 Application Layer (`src/xrate/application/`)
- **RatesService**: Core business logic, provider orchestration
- **StateManager**: Manages market state with persistence
- **StatsTracker**: Tracks bot activity, posts, errors, provider usage
- **HealthChecker**: Monitors system and API health

### 🌐 Adapters Layer (`src/xrate/adapters/`)
- **Providers**: External API integrations (BRS, FastForex, Navasan, Wallex)
- **Telegram**: Bot handlers, jobs, and messaging
- **Formatting**: Message formatting and presentation
- **Persistence**: File-based storage (JSON)
- **AI**: Avalai API integration (optional)

### 🔧 Shared Layer (`src/xrate/shared/`)
- **Validators**: Input validation and security
- **Rate Limiter**: Prevents abuse with per-user rate limiting
- **Language Manager**: Multi-language support
- **Logging**: Structured logging configuration

---

## Key Architectural Principles

1. **Dependency Inversion**: High-level modules don't depend on low-level modules; both depend on abstractions
2. **Separation of Concerns**: Each layer has a single, well-defined responsibility
3. **Testability**: Business logic is isolated and easily testable
4. **Flexibility**: Easy to swap implementations (e.g., different storage backends)
5. **Maintainability**: Clear boundaries between layers make code easy to understand and modify

---

## Error Handling Strategy

- **Domain Errors**: Business logic exceptions (defined in `domain/errors.py`)
- **Provider Errors**: Graceful fallback chains (BRS → FastForex/Navasan)
- **Persistence Errors**: Corruption recovery with backup files
- **Network Errors**: Timeout handling, retry logic, graceful degradation
- **Job Errors**: Non-blocking error handling (Avalai failures don't affect main jobs)

---

## State Management

- **In-Memory State**: `StateManager` maintains current market state
- **Persistent State**: JSON file storage (`last_state.json`)
- **Atomic Writes**: Temporary files + atomic rename for corruption prevention
- **State Recovery**: Schema validation, default values, graceful fallback

---

## Caching Strategy

- **Per-Provider TTL**: Each provider has independent cache TTL (15-28 minutes)
- **Per-Provider Tracking**: Job scheduler respects individual TTLs
- **Global Post Interval**: Automatically calculated as `min(all TTLs)`
- **Cache Validation**: TTL-based expiration checking

---

## Rate Limiting Architecture

- **Namespaced Buckets**: Separate buckets for public/admin/health commands
- **Per-User Limits**: Individual rate limits per user ID
- **Per-Chat Limits**: Health checks use chat ID to prevent group spam
- **Automatic Blocking**: 5-minute blocks for excessive usage

---

## Testing Strategy

- **Unit Tests**: Isolated component testing (domain, application, adapters)
- **Integration Tests**: Provider chains, service orchestration
- **E2E Tests**: Full workflow testing
- **Mock Strategy**: Providers easily mockable via protocols/interfaces

