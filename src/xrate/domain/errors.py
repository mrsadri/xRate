# src/xrate/domain/errors.py
"""
Domain Errors - Business Logic Exceptions

This module defines domain-specific exceptions that represent
business rule violations and domain errors.
"""


class DomainError(Exception):
    """Base exception for domain errors."""
    pass


class InvalidRateError(DomainError):
    """Raised when a rate value is invalid (e.g., negative or zero)."""
    pass


class ProviderUnavailableError(DomainError):
    """Raised when a provider is unavailable."""
    pass


class StateNotFoundError(DomainError):
    """Raised when requested state cannot be found."""
    pass

