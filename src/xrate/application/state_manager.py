# src/xrate/application/state_manager.py
"""
State Manager - Centralized Market State Management

This module provides centralized state management for the bot's market data.
It replaces global variables with a proper state management system that
handles persistence, loading, and state updates across the application.

Files that USE this module:
- xrate.adapters.telegram.handlers (uses state_manager for baseline data)
- xrate.adapters.telegram.jobs (uses state_manager for state updates)
- xrate.application.health (uses state_manager for health checks)

Files that this module USES:
- xrate.adapters.persistence.file_store (load_last, save_last, LastSnapshot for persistence)
- xrate.domain.models (MarketState domain model)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from xrate.adapters.persistence.file_store import LastSnapshot, load_last, save_last

logger = logging.getLogger(__name__)


# Note: We use a non-frozen MarketState here for StateManager's internal use
# The domain.models.MarketState is frozen (immutable), but StateManager needs
# to update state frequently, so we keep a local non-frozen version here.

@dataclass
class MarketState:
    """Represents the current market state with all relevant rates (non-frozen for updates)."""
    usd_toman: int
    eur_toman: int
    gold_1g_toman: int
    eurusd_rate: float
    tether_price_toman: int = 0  # USDT price in Toman
    tether_24h_ch: float = 0.0  # 24-hour change percentage from Wallex API
    ts: Optional[datetime] = None  # Will be set by from_last_snapshot if not provided

    def to_last_snapshot(self) -> LastSnapshot:
        """
        Convert MarketState to LastSnapshot for persistence.
        
        Returns:
            LastSnapshot instance with same data
        """
        return LastSnapshot(
            usd_toman=self.usd_toman,
            eur_toman=self.eur_toman,
            gold_1g_toman=self.gold_1g_toman,
            eurusd_rate=self.eurusd_rate,
            tether_price_toman=self.tether_price_toman,
            tether_24h_ch=self.tether_24h_ch,
            ts=self.ts,
        )

    @classmethod
    def from_last_snapshot(cls, snapshot: LastSnapshot) -> MarketState:
        """
        Create MarketState from LastSnapshot.
        
        Args:
            snapshot: LastSnapshot instance to convert
            
        Returns:
            MarketState instance with same data
        """
        return cls(
            usd_toman=snapshot.usd_toman,
            eur_toman=snapshot.eur_toman,
            gold_1g_toman=snapshot.gold_1g_toman,
            eurusd_rate=snapshot.eurusd_rate,
            tether_price_toman=snapshot.tether_price_toman,
            tether_24h_ch=snapshot.tether_24h_ch,
            ts=snapshot.ts,
        )


class StateManager:
    """Manages the bot's market state with persistence."""
    
    def __init__(self):
        """
        Initialize state manager and load persisted state if available.
        """
        self._current_state: Optional[MarketState] = None
        self._load_from_persistence()

    def _load_from_persistence(self) -> None:
        """
        Load state from persistent storage (JSON file).
        
        Silently handles errors - if loading fails, starts with no state.
        """
        try:
            snapshot = load_last()
            if snapshot:
                self._current_state = MarketState.from_last_snapshot(snapshot)
                logger.info("Loaded state from persistence: %s", self._current_state.ts)
            else:
                logger.info("No persisted state found")
        except Exception as e:
            logger.error("Failed to load state from persistence: %s", e)
            self._current_state = None
    
    def get_current_state(self) -> Optional[MarketState]:
        """
        Get the current market state.
        
        Returns:
            Current MarketState if available, None otherwise
        """
        return self._current_state
    
    def update_state(self, usd_toman: int, eur_toman: int, gold_1g_toman: int, 
                    eurusd_rate: float, ts: Optional[datetime] = None,
                    tether_price_toman: int = 0, tether_24h_ch: float = 0.0) -> MarketState:
        """
        Update the current market state and persist it to disk.
        
        Args:
            usd_toman: USD price in Toman
            eur_toman: EUR price in Toman
            gold_1g_toman: 18K gold price per gram in Toman
            eurusd_rate: EUR/USD exchange rate
            ts: Optional timestamp (defaults to current UTC time)
            tether_price_toman: USDT price in Toman (default: 0)
            tether_24h_ch: 24-hour change percentage from Wallex API (default: 0.0)
            
        Returns:
            New MarketState instance
            
        Note:
            State is persisted even if disk write fails (in-memory state is always updated)
        """
        if ts is None:
            ts = datetime.now(timezone.utc)
        
        new_state = MarketState(
            usd_toman=usd_toman,
            eur_toman=eur_toman,
            gold_1g_toman=gold_1g_toman,
            eurusd_rate=eurusd_rate,
            tether_price_toman=tether_price_toman,
            tether_24h_ch=tether_24h_ch,
            ts=ts,
        )
        
        try:
            save_last(new_state.to_last_snapshot())
            self._current_state = new_state
            logger.info("State updated and persisted: %s", ts)
        except Exception as e:
            logger.error("Failed to persist state: %s", e)
            # Still update in-memory state even if persistence fails
            self._current_state = new_state
        
        return new_state
    
    def has_state(self) -> bool:
        """
        Check if we have a current state available.
        
        Returns:
            True if state exists, False otherwise
        """
        return self._current_state is not None
    
    def get_elapsed_seconds(self) -> int:
        """
        Get seconds elapsed since last state update.
        
        Returns:
            Number of seconds elapsed (0 if no state exists)
        """
        if not self._current_state or not self._current_state.ts:
            return 0
        return int((datetime.now(timezone.utc) - self._current_state.ts).total_seconds())


# Global state manager instance
state_manager = StateManager()
