# src/xrate/adapters/providers/__init__.py
"""
Provider Adapters - External API Clients

This package contains adapters for external exchange rate APIs.
All providers implement the RateProvider protocol.
"""

from xrate.adapters.providers.base import RateProvider
from xrate.adapters.providers.brsapi import BRSAPIProvider
from xrate.adapters.providers.fastforex import FastForexProvider
from xrate.adapters.providers.navasan import NavasanProvider
from xrate.adapters.providers.wallex import WallexProvider

__all__ = [
    "RateProvider",
    "BRSAPIProvider",
    "FastForexProvider",
    "NavasanProvider",
    "WallexProvider",
]

