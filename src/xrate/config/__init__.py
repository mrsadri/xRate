# src/xrate/config/__init__.py
"""
Configuration Module

Provides centralized configuration management using Pydantic Settings.
Supports environment variables and optional YAML configuration overlays.
"""

from xrate.config.settings import Settings, settings

__all__ = ["Settings", "settings"]

