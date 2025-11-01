# src/xrate/shared/rate_limiter.py
"""
Rate Limiter - Abuse Prevention and Resource Protection

This module implements a rate limiting system to prevent abuse and protect
bot resources. It provides per-user rate limiting with configurable limits
for different types of commands and automatic blocking for excessive usage.

Files that USE this module:
- xrate.adapters.telegram.handlers (uses rate_limiter and RATE_LIMITS for all commands)

Files that this module USES:
- None (pure utility implementation)
"""
import time
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int
    time_window: int  # in seconds
    block_duration: int = 300  # 5 minutes default


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._blocked: Dict[str, float] = {}
    
    def is_allowed(self, identifier: str, config: RateLimitConfig) -> bool:
        """
        Check if a request is allowed for the given identifier.
        
        Args:
            identifier: Unique identifier (e.g., user_id)
            config: Rate limit configuration
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        
        # Check if currently blocked
        if identifier in self._blocked:
            if now < self._blocked[identifier]:
                return False
            else:
                # Block period expired, remove from blocked list
                del self._blocked[identifier]
        
        # Clean old requests outside the time window
        cutoff = now - config.time_window
        requests = self._requests[identifier]
        
        # Remove old requests
        while requests and requests[0] < cutoff:
            requests.popleft()
        
        # Check if we're within the limit
        if len(requests) >= config.max_requests:
            # Rate limit exceeded, block the user
            self._blocked[identifier] = now + config.block_duration
            return False
        
        # Add current request
        requests.append(now)
        return True
    
    def get_remaining_requests(self, identifier: str, config: RateLimitConfig) -> int:
        """
        Get remaining requests available for an identifier within the time window.
        
        Args:
            identifier: Unique identifier (e.g., user_id)
            config: Rate limit configuration
            
        Returns:
            Number of remaining requests (0 or positive)
        """
        now = time.time()
        cutoff = now - config.time_window
        requests = self._requests[identifier]
        
        # Clean old requests
        while requests and requests[0] < cutoff:
            requests.popleft()
        
        return max(0, config.max_requests - len(requests))
    
    def get_reset_time(self, identifier: str, config: RateLimitConfig) -> Optional[float]:
        """
        Get when the rate limit window resets for an identifier.
        
        Args:
            identifier: Unique identifier (e.g., user_id)
            config: Rate limit configuration
            
        Returns:
            Unix timestamp when rate limit resets, or None if not currently limited
        """
        if identifier in self._blocked:
            return self._blocked[identifier]
        
        requests = self._requests[identifier]
        if not requests:
            return None
        
        # Return time when oldest request expires
        return requests[0] + config.time_window


# Global rate limiter instance
rate_limiter = RateLimiter()

# Predefined rate limit configurations
RATE_LIMITS = {
    "user_command": RateLimitConfig(max_requests=10, time_window=60),  # 10 requests per minute
    "admin_command": RateLimitConfig(max_requests=30, time_window=60),  # 30 requests per minute
    "health_check": RateLimitConfig(max_requests=5, time_window=60),   # 5 health checks per minute
}
