# src/xrate/shared/__init__.py
"""
Shared Utilities - Cross-cutting Concerns

This package contains shared utilities used across all layers:
- Validation
- Rate limiting
- Language management
- Logging configuration
"""

from xrate.shared.validators import (
    sanitize_user_input,
    validate_api_key,
    validate_bot_token,
    validate_channel_id,
    validate_numeric_input,
    validate_username,
)
from xrate.shared.rate_limiter import rate_limiter, RATE_LIMITS
from xrate.shared.language import (
    get_language,
    set_language,
    translate,
    LANG_ENGLISH,
    LANG_FARSI,
)

__all__ = [
    "validate_bot_token",
    "validate_channel_id",
    "validate_api_key",
    "validate_username",
    "validate_numeric_input",
    "sanitize_user_input",
    "rate_limiter",
    "RATE_LIMITS",
    "get_language",
    "set_language",
    "translate",
    "LANG_ENGLISH",
    "LANG_FARSI",
]

