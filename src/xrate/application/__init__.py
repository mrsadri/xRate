# src/xrate/application/__init__.py
"""
Application Layer - Use Cases and Services

This package contains application services that orchestrate domain logic.
No direct I/O dependencies - uses adapters through interfaces.
"""

from xrate.application.rates_service import RatesService, get_irr_snapshot, ProviderChain
from xrate.application.state_manager import StateManager, state_manager
from xrate.application.stats import StatsTracker, stats_tracker
from xrate.application.crawler_service import get_crawler_snapshot

__all__ = [
    "RatesService",
    "get_irr_snapshot",
    "get_crawler_snapshot",
    "ProviderChain",
    "StateManager",
    "state_manager",
    "StatsTracker",
    "stats_tracker",
]

