# src/xrate/adapters/persistence/file_store.py
"""
File Store - State Persistence and Data Storage

This module handles persistent storage of market state data using JSON files.
It provides functionality to save and load the last announced market state,
enabling the bot to track changes and calculate percentage differences.

Files that USE this module:
- xrate.application.state_manager (StateManager uses save_last and load_last)
- xrate.adapters.telegram.jobs (uses save_last and LastSnapshot)
- xrate.adapters.telegram.handlers (uses load_last and LastSnapshot)

Files that this module USES:
- xrate.config (settings for file paths)
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from xrate.config import settings


@dataclass
class LastSnapshot:
    usd_toman: int
    eur_toman: int
    gold_1g_toman: int
    eurusd_rate: float
    tether_price_toman: int = 0  # USDT price in Toman
    tether_24h_ch: float = 0.0  # 24-hour change percentage from Wallex API
    ts: Optional[datetime] = None  # UTC - will be set by from_json if not provided

    def to_json(self) -> dict:
        """
        Convert LastSnapshot to JSON-serializable dictionary.
        
        Returns:
            Dictionary with ISO-formatted timestamp
        """
        d = asdict(self)
        if self.ts:
            d["ts"] = self.ts.isoformat()
        else:
            d["ts"] = datetime.now(timezone.utc).isoformat()
        return d

    @staticmethod
    def from_json(data: dict) -> "LastSnapshot":
        """
        Create LastSnapshot from JSON dictionary.
        
        Args:
            data: Dictionary with market data and timestamp
            
        Returns:
            LastSnapshot instance with parsed data
        """
        ts_raw = data.get("ts")
        # Accept both "...Z" and "+00:00"
        if isinstance(ts_raw, str):
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            ts = ts.astimezone(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        return LastSnapshot(
            usd_toman=int(data["usd_toman"]),
            eur_toman=int(data["eur_toman"]),
            gold_1g_toman=int(data["gold_1g_toman"]),
            eurusd_rate=float(data["eurusd_rate"]),
            tether_price_toman=int(data.get("tether_price_toman", 0)),
            tether_24h_ch=float(data.get("tether_24h_ch", 0.0)),
            ts=ts,
        )


def _state_path() -> Path:
    """
    Get path to state file and ensure directory exists.
    
    Returns:
        Path object pointing to state file
    """
    p = settings.last_state_file
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_last(snap: LastSnapshot) -> None:
    """
    Save last snapshot to persistent storage (JSON file) using atomic write.
    
    Uses temporary file + atomic rename to prevent race conditions and corrupted files.
    
    Args:
        snap: LastSnapshot instance to save
    """
    p = _state_path()
    
    # Atomic write: write to temp file first, then rename atomically
    temp_dir = p.parent
    temp_fd, temp_path = tempfile.mkstemp(
        suffix=".json.tmp",
        dir=str(temp_dir),
        text=True
    )
    
    try:
        # Write to temp file
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(snap.to_json(), f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        # Atomic rename (replaces target file atomically on Unix/Windows)
        os.replace(temp_path, str(p))
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise RuntimeError(f"Failed to save state file: {e}") from e


def load_last() -> Optional[LastSnapshot]:
    """
    Load last snapshot from persistent storage.
    
    Handles corrupt files gracefully by:
    1. Attempting to load the file
    2. If JSON decode fails, backing up the corrupt file and returning None
    3. If schema validation fails, using defaults for missing fields
    
    Returns:
        LastSnapshot if file exists and is valid, None otherwise
    """
    import logging
    log = logging.getLogger(__name__)
    
    p = _state_path()
    if not p.exists():
        return None
    
    try:
        with p.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                # Corrupt JSON - backup and return None
                backup_path = p.with_suffix(".json.corrupt")
                try:
                    import shutil
                    shutil.copy2(p, backup_path)
                    log.warning("State file corrupted (JSON decode error), backed up to %s: %s", 
                               backup_path, e)
                    # Remove corrupt file
                    p.unlink()
                except Exception as backup_error:
                    log.error("Failed to backup corrupt state file: %s", backup_error)
                return None
        
        try:
            return LastSnapshot.from_json(data)
        except (KeyError, ValueError, TypeError) as e:
            # Schema mismatch - try to recover with defaults
            log.warning("State file schema mismatch, attempting recovery: %s", e)
            try:
                # Attempt to create snapshot with defaults for missing fields
                return LastSnapshot.from_json({
                    "usd_toman": data.get("usd_toman", 0),
                    "eur_toman": data.get("eur_toman", 0),
                    "gold_1g_toman": data.get("gold_1g_toman", 0),
                    "eurusd_rate": data.get("eurusd_rate", 0.0),
                    "tether_price_toman": data.get("tether_price_toman", 0),
                    "tether_24h_ch": data.get("tether_24h_ch", 0.0),
                    "ts": data.get("ts"),
                })
            except Exception as recovery_error:
                log.error("Failed to recover state file: %s", recovery_error)
                return None
    except Exception as e:
        # Any other error - log and return None
        log.error("Unexpected error loading state file: %s", e, exc_info=True)
        return None
