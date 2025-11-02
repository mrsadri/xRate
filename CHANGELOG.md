# Changelog

All notable changes to XRate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-11-XX

### 🐛 Fixed - Critical Bug Fixes

#### 1. Threshold Flip-Flop (Floating Precision)
- **Fixed**: Added `Decimal`-based calculations with hysteresis to prevent rapid on/off posting
- **Impact**: Eliminates spam from floating-point precision issues near threshold boundaries
- **Implementation**: 
  - Uses `Decimal` for precise threshold calculations
  - Implements hysteresis requiring +0.2% extra movement after first breach
  - Tracks breach history per instrument to prevent flip-flop behavior

#### 2. Auto Post Interval Respects Per-Provider TTLs
- **Fixed**: Implemented per-provider TTL tracking to prevent rate limiting
- **Impact**: Providers with longer cache windows (e.g., Navasan with 28-minute TTL) are no longer polled too frequently
- **Implementation**:
  - Added `_should_fetch_provider()` function to track next-eligible time per provider
  - Job scheduler now respects individual provider TTLs even when global post interval is shorter
  - Prevents 429 errors and API bans from providers with longer cache windows

#### 3. State File Corruption Recovery
- **Fixed**: Enhanced state file loading with graceful corruption handling
- **Impact**: Bot can now recover from corrupted state files without manual intervention
- **Implementation**:
  - Automatic backup of corrupt files to `.json.corrupt`
  - Schema validation with default value recovery
  - Graceful fallback to None when corruption cannot be recovered

#### 4. DST/Timezone Bug in Daily Summary
- **Fixed**: Daily summary job now uses timezone-aware scheduling
- **Impact**: Prevents duplicate or missed daily reports during DST transitions
- **Implementation**:
  - Uses `zoneinfo.ZoneInfo` for timezone-aware scheduling
  - Defaults to UTC but can be configured for local timezone

#### 5. Provider Schema Drift Resilience
- **Fixed**: Added robust parsing with normalization for API schema changes
- **Impact**: Bot continues working even when providers change field names or data formats
- **Implementation**:
  - `_normalize_price_value()` handles string formats like "108.4K"
  - Multiple field name fallbacks (price, value, value_price, last_price)
  - Alternative symbol name matching (e.g., gold18, gold_18k, IR_GOLD18K)

#### 6. Wallex Exception Blocking
- **Fixed**: Made Tether data truly optional with guarded fetch and formatting
- **Impact**: Wallex failures no longer block entire price posts
- **Implementation**:
  - Wrapped Wallex fetch in try/except blocks
  - Fallback formatting that omits Tether if unavailable
  - Provider attribution only added when data is successfully fetched

#### 7. Rate Limiter Mismatch
- **Fixed**: Implemented namespaced rate limiting buckets
- **Impact**: Admin commands and public commands now have independent rate limits
- **Implementation**:
  - `public:user:{user_id}` for public commands
  - `admin:user:{user_id}` for admin commands (separate bucket)
  - `health:chat:{chat_id}` for health checks (prevents group spam)

#### 8. Avalai Failure Cascading
- **Fixed**: Made Avalai analysis completely non-blocking
- **Impact**: Avalai API failures no longer mark jobs as failed or cause duplicate posts
- **Implementation**:
  - Comprehensive try/except with 30-second timeout
  - Never fails main job after successful price post
  - All errors logged as warnings, not exceptions

### ✨ Added - New Features

- **Comprehensive Function Documentation**: All functions now have detailed docstrings following consistent style
- **Architecture Documentation**: New `docs/ARCHITECTURE.md` with detailed architecture diagrams and design patterns
- **API Provider Documentation**: New `docs/API_PROVIDERS.md` with detailed provider information
- **Enhanced Error Handling**: Better error messages and recovery mechanisms throughout

### 📚 Documentation Improvements

- **Streamlined README**: Reduced from ~1000 to ~300 lines with better organization
- **Table of Contents**: Added navigable TOC to README
- **Separated Documentation**: Moved detailed sections to separate markdown files
- **Type Hints**: Added type ignore comments for telegram imports to fix IDE warnings

### 🔧 Code Quality

- **Code Review**: Comprehensive review of all modules
- **Linting**: All files pass linting checks
- **Type Safety**: Improved type hints and type checking
- **Error Handling**: More robust error handling throughout codebase

### 🏗️ Architecture

- **Per-Provider TTL Tracking**: New architecture component for respecting individual provider cache windows
- **Hysteresis System**: New threshold breach tracking system to prevent flip-flop behavior
- **Namespaced Rate Limiting**: Enhanced rate limiter with bucket namespacing

### 🔒 Security

- **Enhanced Rate Limiting**: Namespaced buckets prevent rate limit interference between user types
- **Improved Input Validation**: Better validation for provider data formats
- **Secure Error Messages**: No sensitive data exposed in error messages

### ⚡ Performance

- **Smarter Provider Fetching**: Only fetch providers when their TTL has elapsed
- **Reduced API Calls**: Per-provider TTL tracking prevents unnecessary API requests
- **Optimized Threshold Calculations**: Decimal-based calculations reduce computational overhead

---

## [1.0.0] - 2025-11-XX

### 🎉 Initial Release

- **Core Functionality**: EUR→USD exchange rate monitoring and Iranian market data tracking
- **Multi-Provider Support**: BRS API, FastForex, Navasan, Wallex with intelligent fallback
- **Smart Posting**: Configurable percentage thresholds for automatic market updates
- **Interactive Commands**: `/start`, `/irr`, `/health`, `/post`, `/language`
- **Health Monitoring**: Real-time system health checks and API status
- **Statistics Tracking**: Activity tracking with daily summaries
- **Multi-language Support**: English and Farsi (فارسی)
- **AI Analysis**: Optional Farsi market analysis via Avalai API
- **Clean Architecture**: Layered architecture with dependency inversion
- **Comprehensive Testing**: 100+ test cases with pytest
- **Production Ready**: Full server deployment support with systemd/Supervisor

---

## Version History

- **1.1.0** - Major bug fixes and documentation improvements
- **1.0.0** - Initial stable release

---

## Migration Guide

### Upgrading from 1.0.0 to 1.1.0

No breaking changes! This is a backward-compatible update.

**Recommended Actions:**
1. Update your code to use the new bug fixes
2. Review the new documentation files (`docs/ARCHITECTURE.md`, `docs/API_PROVIDERS.md`)
3. No configuration changes required
4. Existing state files will be automatically migrated if corrupted

**Behavior Changes:**
- Threshold breaches now require +0.2% extra movement after first breach (hysteresis)
- Providers with longer TTLs are now respected individually
- State file corruption is now handled automatically with backups
- Daily summaries now handle DST transitions correctly
- Rate limiting now uses namespaced buckets (better isolation)

---

## Contributors

- Masih Sadri - Project maintainer and initial development

---

## Links

- [GitHub Repository](https://github.com/mrsadri/xRate)
- [Documentation](README.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [API Providers Documentation](docs/API_PROVIDERS.md)

