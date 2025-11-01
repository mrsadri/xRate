#!/usr/bin/env python3
"""
Migration Script - Restructure Project to Clean Architecture

This script moves files to the new structure and updates imports.
Run this once to migrate the codebase.
"""

import os
import re
import shutil
from pathlib import Path

# File mapping: (source, destination, import_updates)
MIGRATIONS = [
    # Shared utilities
    ("utils/validators.py", "src/xrate/shared/validators.py", [
        (r"from utils\.validators", "from xrate.shared.validators"),
        (r"import utils\.validators", "import xrate.shared.validators"),
    ]),
    ("utils/rate_limiter.py", "src/xrate/shared/rate_limiter.py", [
        (r"from utils\.rate_limiter", "from xrate.shared.rate_limiter"),
    ]),
    ("utils/language.py", "src/xrate/shared/language.py", [
        (r"from utils\.language", "from xrate.shared.language"),
    ]),
    ("logging_conf.py", "src/xrate/shared/logging_conf.py", [
        (r"from logging_conf", "from xrate.shared.logging_conf"),
        (r"import logging_conf", "import xrate.shared.logging_conf"),
    ]),
    
    # Application services
    ("services/rates.py", "src/xrate/application/rates_service.py", [
        (r"from providers\.", "from xrate.adapters.providers."),
        (r"from services\.cache", "from xrate.adapters.persistence.cache"),
        (r"import providers\.", "import xrate.adapters.providers."),
        (r"import services\.cache", "import xrate.adapters.persistence.cache"),
    ]),
    ("services/state_manager.py", "src/xrate/application/state_manager.py", [
        (r"from services\.cache", "from xrate.adapters.persistence.cache"),
        (r"from \.cache", "from xrate.adapters.persistence.cache"),
    ]),
    ("services/stats.py", "src/xrate/application/stats.py", []),
    ("services/admin_store.py", "src/xrate/adapters/persistence/admin_store.py", []),
    
    # Adapters - Providers (already copied, just update imports)
    # We'll handle providers separately
    
    # Adapters - Telegram
    ("tg/handlers.py", "src/xrate/adapters/telegram/handlers.py", [
        (r"from services\.rates", "from xrate.application.rates_service"),
        (r"from services\.state_manager", "from xrate.application.state_manager"),
        (r"from services\.admin_store", "from xrate.adapters.persistence.admin_store"),
        (r"from formatting\.formatter", "from xrate.adapters.formatting.formatter"),
        (r"from utils\.", "from xrate.shared."),
        (r"from config import", "from xrate.config import"),
    ]),
    ("tg/jobs.py", "src/xrate/adapters/telegram/jobs.py", [
        (r"from formatting\.formatter", "from xrate.adapters.formatting.formatter"),
        (r"from services\.rates", "from xrate.application.rates_service"),
        (r"from services\.state_manager", "from xrate.application.state_manager"),
        (r"from services\.stats", "from xrate.application.stats"),
        (r"from services\.admin_store", "from xrate.adapters.persistence.admin_store"),
        (r"from providers\.wallex", "from xrate.adapters.providers.wallex"),
        (r"from config import", "from xrate.config import"),
    ]),
    
    # Adapters - Formatting
    ("formatting/formatter.py", "src/xrate/adapters/formatting/formatter.py", [
        (r"from services\.rates", "from xrate.application.rates_service"),
        (r"from utils\.language", "from xrate.shared.language"),
    ]),
    
    # Adapters - Persistence
    ("services/cache.py", "src/xrate/adapters/persistence/file_store.py", [
        (r"from config import", "from xrate.config import"),
    ]),
]

def update_imports(content: str, updates: list) -> str:
    """Update imports in file content."""
    for pattern, replacement in updates:
        content = re.sub(pattern, replacement, content)
    return content

def migrate_file(source: Path, dest: Path, import_updates: list):
    """Migrate a single file with import updates."""
    if not source.exists():
        print(f"⚠️  Source not found: {source}")
        return
    
    # Create destination directory
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Read source
    content = source.read_text(encoding="utf-8")
    
    # Update imports
    content = update_imports(content, import_updates)
    
    # Write destination
    dest.write_text(content, encoding="utf-8")
    print(f"✅ Migrated: {source} -> {dest}")

def main():
    """Run the migration."""
    root = Path(__file__).parent.parent
    os.chdir(root)
    
    print("Starting migration...")
    
    for source_rel, dest_rel, updates in MIGRATIONS:
        source = root / source_rel
        dest = root / dest_rel
        migrate_file(source, dest, updates)
    
    # Update provider imports
    providers_dir = root / "src/xrate/adapters/providers"
    for provider_file in providers_dir.glob("*.py"):
        if provider_file.name == "__init__.py" or provider_file.name == "base.py":
            continue
        content = provider_file.read_text(encoding="utf-8")
        content = re.sub(
            r"from \.base import",
            "from xrate.adapters.providers.base import",
            content
        )
        content = re.sub(
            r"from config import",
            "from xrate.config import",
            content
        )
        provider_file.write_text(content, encoding="utf-8")
        print(f"✅ Updated imports in: {provider_file}")
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    main()

