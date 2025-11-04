# src/xrate/config/settings.py
"""
Settings - Pydantic-based Configuration Management

Provides centralized configuration management using Pydantic Settings.
Supports environment variables with validation and optional YAML overlays.

Files that USE this module:
- xrate.app (loads settings for bot configuration)
- xrate.adapters.providers.* (all providers use settings for API keys and URLs)
- xrate.adapters.telegram.* (telegram handlers and jobs use settings)
- xrate.application.* (services use settings for configuration)

Files that this module USES:
- xrate.shared.validators (validation functions for settings)
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

import os  # Operating system interface for environment variables
from pathlib import Path  # Object-oriented filesystem paths
from typing import Optional  # Type hints for optional values

from pydantic import Field, field_validator  # Data validation and field configuration
from pydantic_settings import BaseSettings, SettingsConfigDict  # Settings management with Pydantic

from xrate.shared.validators import (
    validate_api_key,  # Validate API key format
    validate_bot_token,  # Validate Telegram bot token format
    validate_channel_id,  # Validate Telegram channel ID format
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # --- Telegram ---
    bot_token: str = Field(..., alias="BOT_TOKEN")
    channel_id: str = Field(..., alias="CHANNEL_ID")
    admin_username: str = Field(default="MasihSadri", alias="ADMIN_USERNAME")
    
    # --- API Providers ---
    fastforex_key: str = Field(..., alias="FASTFOREX_KEY")
    navasan_key: str = Field(..., alias="NAVASAN_API_KEY")
    brsapi_key: str = Field(default="", alias="BRSAPI_KEY")
    
    # --- Avalai API (for market analysis) ---
    avalai_key: str = Field(default="", alias="AVALAI_KEY")
    
    # --- HTTP Settings ---
    http_timeout_seconds: int = Field(default=10, alias="HTTP_TIMEOUT_SECONDS", ge=1, le=60)
    
    # --- Scheduling ---
    # post_interval_minutes is now calculated automatically as min of cache settings
    # Removed from Field() - will be computed property
    
    # --- Cache Settings (in minutes) ---
    fastforex_cache_minutes: int = Field(default=15, alias="FASTFOREX_CACHE_MINUTES", ge=1, le=1440)
    navasan_cache_minutes: int = Field(default=28, alias="NAVASAN_CACHE_MINUTES", ge=1, le=1440)
    brsapi_cache_minutes: int = Field(default=15, alias="BRSAPI_CACHE_MINUTES", ge=1, le=1440)
    wallex_cache_minutes: int = Field(default=15, alias="WALLEX_CACHE_MINUTES", ge=1, le=1440)
    
    # --- Crawler Settings ---
    crawler1_url: str = Field(default="https://www.bonbast.com/", alias="CRAWLER1_URL")
    crawler1_interval_minutes: int = Field(default=37, alias="CRAWLER1_INTERVAL_MINUTES", ge=1, le=1440)
    crawler2_url: str = Field(default="https://alanchand.com/", alias="CRAWLER2_URL")
    crawler2_interval_minutes: int = Field(default=43, alias="CRAWLER2_INTERVAL_MINUTES", ge=1, le=1440)
    
    # --- Announcement Thresholds (% vs last announced) ---
    margin_usd_upper_pct: float = Field(default=1.0, alias="MARGIN_USD_UPPER_PCT", ge=0.0)
    margin_usd_lower_pct: float = Field(default=2.0, alias="MARGIN_USD_LOWER_PCT", ge=0.0)
    margin_eur_upper_pct: float = Field(default=1.0, alias="MARGIN_EUR_UPPER_PCT", ge=0.0)
    margin_eur_lower_pct: float = Field(default=2.0, alias="MARGIN_EUR_LOWER_PCT", ge=0.0)
    margin_gold_upper_pct: float = Field(default=1.0, alias="MARGIN_GOLD_UPPER_PCT", ge=0.0)
    margin_gold_lower_pct: float = Field(default=2.0, alias="MARGIN_GOLD_LOWER_PCT", ge=0.0)
    margin_eurusd_upper_pct: float = Field(default=1.0, alias="MARGIN_EURUSD_UPPER_PCT", ge=0.0)
    margin_eurusd_lower_pct: float = Field(default=2.0, alias="MARGIN_EURUSD_LOWER_PCT", ge=0.0)
    margin_tether_upper_pct: float = Field(default=1.0, alias="MARGIN_TETHER_UPPER_PCT", ge=0.0)
    margin_tether_lower_pct: float = Field(default=2.0, alias="MARGIN_TETHER_LOWER_PCT", ge=0.0)
    
    # --- Persistence ---
    last_state_file: Path = Field(
        default=Path("./data/last_state.json"), alias="LAST_STATE_FILE"
    )
    
    # --- Logging (for server deployment) ---
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")
    log_dir: Optional[str] = Field(default=None, alias="LOG_DIR")
    log_stdout: bool = Field(default=True, alias="XRATE_LOG_STDOUT")
    log_max_bytes: int = Field(default=10 * 1024 * 1024, alias="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    
    # Computed properties for convenience (maintain backward compatibility)
    @property
    def FASTFOREX_URL(self) -> str:
        """FastForex API URL with key."""
        return f"https://api.fastforex.io/fetch-all?api_key={self.fastforex_key}"
    
    @property
    def NAVASAN_URL(self) -> str:
        """Navasan API URL with key."""
        return f"http://api.navasan.tech/latest/?api_key={self.navasan_key}"
    
    @property
    def BRSAPI_URL(self) -> str:
        """BRS API URL with key."""
        return f"https://brsapi.ir/Api/Market/Gold_Currency.php?key={self.brsapi_key}"
    
    @property
    def WALLEX_URL(self) -> str:
        """Wallex API URL."""
        return "https://api.wallex.ir/v1/markets"
    
    # Backward compatibility aliases
    @property
    def BOT_TOKEN(self) -> str:
        return self.bot_token
    
    @property
    def CHANNEL_ID(self) -> str:
        return self.channel_id
    
    @property
    def ADMIN_USERNAME(self) -> str:
        return self.admin_username
    
    @property
    def FASTFOREX_KEY(self) -> str:
        return self.fastforex_key
    
    @property
    def NAVASAN_KEY(self) -> str:
        return self.navasan_key
    
    @property
    def BRSAPI_KEY(self) -> str:
        return self.brsapi_key
    
    @property
    def HTTP_TIMEOUT_SECONDS(self) -> int:
        return self.http_timeout_seconds
    
    @property
    def post_interval_minutes(self) -> int:
        """
        Calculate posting interval as minimum of all cache TTLs.
        
        This ensures we don't check more frequently than data is refreshed,
        preventing unnecessary API calls.
        
        Returns:
            Minimum cache TTL in minutes (from FastForex, Navasan, BRS API, and Wallex)
        """
        cache_intervals = [
            self.fastforex_cache_minutes,
            self.navasan_cache_minutes,
            self.brsapi_cache_minutes,
            self.wallex_cache_minutes,
        ]
        return min(cache_intervals)
    
    @property
    def POST_INTERVAL_MINUTES(self) -> int:
        """Backward compatibility alias."""
        return self.post_interval_minutes
    
    @property
    def FASTFOREX_CACHE_MINUTES(self) -> int:
        return self.fastforex_cache_minutes
    
    @property
    def NAVASAN_CACHE_MINUTES(self) -> int:
        return self.navasan_cache_minutes
    
    @property
    def BRSAPI_CACHE_MINUTES(self) -> int:
        return self.brsapi_cache_minutes
    
    @property
    def WALLEX_CACHE_MINUTES(self) -> int:
        return self.wallex_cache_minutes
    
    @property
    def CRAWLER1_URL(self) -> str:
        return self.crawler1_url
    
    @property
    def CRAWLER1_INTERVAL_MINUTES(self) -> int:
        return self.crawler1_interval_minutes
    
    @property
    def CRAWLER2_URL(self) -> str:
        return self.crawler2_url
    
    @property
    def CRAWLER2_INTERVAL_MINUTES(self) -> int:
        return self.crawler2_interval_minutes
    
    @property
    def MARGIN_USD_UPPER_PCT(self) -> float:
        return self.margin_usd_upper_pct
    
    @property
    def MARGIN_USD_LOWER_PCT(self) -> float:
        return self.margin_usd_lower_pct
    
    @property
    def MARGIN_EUR_UPPER_PCT(self) -> float:
        return self.margin_eur_upper_pct
    
    @property
    def MARGIN_EUR_LOWER_PCT(self) -> float:
        return self.margin_eur_lower_pct
    
    @property
    def MARGIN_GOLD_UPPER_PCT(self) -> float:
        return self.margin_gold_upper_pct
    
    @property
    def MARGIN_GOLD_LOWER_PCT(self) -> float:
        return self.margin_gold_lower_pct
    
    @property
    def MARGIN_EURUSD_UPPER_PCT(self) -> float:
        return self.margin_eurusd_upper_pct
    
    @property
    def MARGIN_EURUSD_LOWER_PCT(self) -> float:
        return self.margin_eurusd_lower_pct
    
    @property
    def MARGIN_TETHER_UPPER_PCT(self) -> float:
        return self.margin_tether_upper_pct
    
    @property
    def MARGIN_TETHER_LOWER_PCT(self) -> float:
        return self.margin_tether_lower_pct
    
    @property
    def LAST_STATE_FILE(self) -> str:
        return str(self.last_state_file)
    
    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Validate bot token format."""
        if not validate_bot_token(v):
            raise ValueError("Invalid BOT_TOKEN format")
        return v
    
    @field_validator("channel_id")
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        """Validate channel ID format."""
        if not validate_channel_id(v):
            raise ValueError("Invalid CHANNEL_ID format")
        return v
    
    @field_validator("fastforex_key", "navasan_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format."""
        if not validate_api_key(v):
            raise ValueError("Invalid API key format")
        return v
    
    @field_validator("brsapi_key")
    @classmethod
    def validate_brsapi_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate BRS API key if provided."""
        if v and not validate_api_key(v):
            raise ValueError("Invalid BRSAPI_KEY format")
        return v
    
    def model_post_init(self, __context) -> None:
        """Post-initialization validation."""
        # Ensure data directory exists
        self.last_state_file.parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


# ============================================================================
# Deployment Instructions
# ============================================================================
#
# How to run the bot in the background with logging:
#
# 1. Run the bot in the background:
#    nohup python -m xrate > bot.log 2>&1 &
#
#    Or using the run script:
#    nohup ./scripts/run.sh > bot.log 2>&1 &
#
# 2. Monitor logs in real-time:
#    tail -f bot.log
#
# 3. Stop the bot:
#    pkill -f "python -m xrate"
#
#    Or stop both the module and old script methods:
#    pkill -f "python -m xrate"; pkill -f run.sh; pkill -f app.py
#
# 4. Check if bot is running:
#    ps aux | grep "python -m xrate"
#
# 5. View latest logs:
#    tail -n 100 bot.log
#
# ============================================================================

