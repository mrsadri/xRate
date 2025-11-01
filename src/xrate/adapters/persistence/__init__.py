# src/xrate/adapters/persistence/__init__.py
"""
Persistence Adapters - Data Storage

This package contains adapters for persisting data:
- File-based storage (JSON)
- Optional Redis storage (future)
"""

from xrate.adapters.persistence.file_store import LastSnapshot, load_last, save_last
from xrate.adapters.persistence.admin_store import AdminStore, admin_store

__all__ = [
    "LastSnapshot",
    "load_last",
    "save_last",
    "AdminStore",
    "admin_store",
]

