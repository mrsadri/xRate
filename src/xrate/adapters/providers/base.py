# src/xrate/adapters/providers/base.py
"""
Base Provider Interface for Exchange Rate Providers

This module defines the abstract base class for all exchange rate providers.
It establishes the contract that all provider implementations must follow.

Files that USE this module:
- xrate.adapters.providers.navasan (NavasanProvider implements RateProvider)
- xrate.adapters.providers.wallex (WallexProvider implements RateProvider)
- xrate.application.rates_service (uses RateProvider protocol)
- tests.test_providers (unit tests)

Files that this module USES:
- None (pure interface definition)
"""
from abc import ABC, abstractmethod

class RateProvider(ABC):
    @abstractmethod
    def eur_usd_rate(self) -> float:
        """Return the USD-per-1-EUR rate as float."""
        raise NotImplementedError
