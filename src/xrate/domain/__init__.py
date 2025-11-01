# src/xrate/domain/__init__.py
"""
Domain Layer - Pure Business Objects

This package contains domain models and business rules.
No dependencies on infrastructure or external systems.
"""

from xrate.domain.models import (
    Change,
    IrrSnapshot,
    MarketState,
    ProviderAttribution,
    Rate,
)
from xrate.domain.errors import (
    DomainError,
    InvalidRateError,
    ProviderUnavailableError,
    StateNotFoundError,
)

__all__ = [
    "Rate",
    "IrrSnapshot",
    "MarketState",
    "Change",
    "ProviderAttribution",
    "DomainError",
    "InvalidRateError",
    "ProviderUnavailableError",
    "StateNotFoundError",
]

