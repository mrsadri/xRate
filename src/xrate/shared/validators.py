# src/xrate/shared/validators.py
"""
Input Validation Utilities - Security and Data Validation

This module provides comprehensive input validation functions for the bot.
It validates bot tokens, channel IDs, API keys, usernames, and numeric inputs
to ensure security and prevent errors from invalid configuration or user input.

Files that USE this module:
- xrate.config.settings (uses validation functions in Settings field validators)

Files that this module USES:
- None (pure utility functions)
"""
import re
from typing import Optional


def validate_channel_id(channel_id: str) -> bool:
    """
    Validate Telegram channel/chat ID format.
    
    Args:
        channel_id: Channel ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not channel_id:
        return False
    
    # Channel IDs can be:
    # - @channelname (public channels)
    # - -1001234567890 (private channels/chats)
    # - 123456789 (user IDs)
    if channel_id.startswith('@'):
        # Public channel: @channelname
        return len(channel_id) > 1 and re.match(r'^@[a-zA-Z0-9_]+$', channel_id)
    elif channel_id.startswith('-100'):
        # Private channel/chat: -1001234567890
        return re.match(r'^-100\d+$', channel_id)
    else:
        # User ID: 123456789
        return re.match(r'^\d+$', channel_id)


def validate_bot_token(token: str) -> bool:
    """
    Validate Telegram bot token format.
    
    Args:
        token: Bot token to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not token:
        return False
    
    # Bot tokens should be in format: 123456789:ABCDEFghijklmnopQRSTUVwxyz
    pattern = r'^\d{8,10}:[A-Za-z0-9_-]{35}$'
    return bool(re.match(pattern, token))


def validate_api_key(api_key: str, min_length: int = 10) -> bool:
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
        min_length: Minimum length requirement
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False
    
    return len(api_key) >= min_length and not api_key.isspace()


def validate_username(username: str) -> bool:
    """
    Validate Telegram username format.
    
    Args:
        username: Username to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False
    
    # Remove @ if present
    clean_username = username.lstrip('@')
    
    # Username should be 5-32 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, clean_username))


def validate_numeric_input(value: str, min_val: Optional[float] = None, 
                          max_val: Optional[float] = None) -> bool:
    """
    Validate numeric input string.
    
    Args:
        value: String value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        True if valid, False otherwise
    """
    if not value:
        return False
    
    try:
        num_val = float(value)
        if min_val is not None and num_val < min_val:
            return False
        if max_val is not None and num_val > max_val:
            return False
        return True
    except ValueError:
        return False


def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()
