# src/xrate/adapters/persistence/admin_store.py
"""
Admin Store - Store Admin User ID for Notifications

This module stores the admin's Telegram user ID so we can send notifications.
The user_id is stored when the admin first uses an admin command.

Files that USE this module:
- xrate.adapters.telegram.handlers (store admin user_id when they use commands)
- xrate.adapters.telegram.jobs (send notifications to admin)

Files that this module USES:
- pathlib (file management)
- json (persistence)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ADMIN_STORE_FILE = Path("./data/admin_store.json")


class AdminStore:
    """Store and retrieve admin user ID."""
    
    def __init__(self, store_file: Path = ADMIN_STORE_FILE):
        """
        Initialize admin store.
        
        Args:
            store_file: Path to JSON file for storing admin data
        """
        self.store_file = store_file
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self._admin_user_id: Optional[int] = None
        self._load()
    
    def _load(self) -> None:
        """Load admin user ID from disk."""
        if not self.store_file.exists():
            logger.info("No admin store file found")
            return
        
        try:
            with self.store_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                user_id = data.get("admin_user_id")
                if user_id:
                    self._admin_user_id = int(user_id)
                    logger.info("Loaded admin user ID: %s", self._admin_user_id)
        except Exception as e:
            logger.error("Failed to load admin store: %s", e)
    
    def _save(self) -> None:
        """Save admin user ID to disk."""
        if self._admin_user_id is None:
            return
        
        try:
            data = {"admin_user_id": self._admin_user_id}
            with self.store_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved admin user ID: %s", self._admin_user_id)
        except Exception as e:
            logger.error("Failed to save admin store: %s", e)
    
    def set_admin_user_id(self, user_id: int) -> None:
        """
        Set and persist admin user ID.
        
        Args:
            user_id: Telegram user ID of the admin
        """
        if self._admin_user_id != user_id:
            self._admin_user_id = user_id
            self._save()
            logger.info("Admin user ID set: %s", user_id)
    
    def get_admin_user_id(self) -> Optional[int]:
        """
        Get stored admin user ID.
        
        Returns:
            Admin user ID or None if not set
        """
        return self._admin_user_id


# Global admin store instance
admin_store = AdminStore()

