# src/xrate/shared/language.py
"""
Language Management - Multi-language Support

This module provides language management functionality for the bot,
including language preference storage and retrieval, and translation
functions for messages.

Files that USE this module:
- xrate.adapters.telegram.handlers (uses get_language, set_language, translate)
- xrate.adapters.formatting.formatter (uses translate for message formatting)

Files that this module USES:
- pathlib (file management)
- json (persistence)
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Language constants
LANG_ENGLISH = "en"
LANG_FARSI = "fa"

# Default language file path
DEFAULT_LANG_FILE = "./data/language.json"

# Translation dictionaries
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    LANG_ENGLISH: {
        "usd_line": "(USD 💵) $1   = {value} KToman        {change}",
        "eur_line": "(Euro 💶) €1  = {value} KToman         {change}",
        "gold_line": "(Gold 🏆) 1gr = {value} MToman     {change}",
        "eurusd_line": "(Euro 💶) €1  = ${value} (USD 💵)  {change}",
        "tether_line": "(Tether 💎) 1 USDT = {value} KToman     {change_pct}% {arrow}",
        "time_elapsed": "Time spent from previous announcement: {elapsed}",
        "reported_by": "Reported by {providers}",
        "no_data": "No market data available",
    },
    LANG_FARSI: {
        "usd_line": "(دلار 💵) ۱ دلار   = {value} هزارتومان        {change}",
        "eur_line": "(یورو 💶) ۱ یورو  = {value} هزارتومان         {change}",
        "gold_line": "(طلا 🏆) ۱ گرم = {value} میلیون‌تومان     {change}",
        "eurusd_line": "(یورو 💶) ۱ یورو  = ${value} (دلار 💵)  {change}",
        "tether_line": "(تتر 💎) ۱ تتر = {value} هزارتومان     {change_pct}% {arrow}",
        "time_elapsed": "زمان سپری شده از اعلامیه قبلی: {elapsed}",
        "reported_by": "گزارش شده توسط {providers}",
        "no_data": "داده‌های بازار در دسترس نیست",
    }
}


class LanguageManager:
    """Manages language preferences with persistence."""
    
    def __init__(self, lang_file: str = DEFAULT_LANG_FILE):
        """
        Initialize language manager.
        
        Args:
            lang_file: Path to language preference file
        """
        self.lang_file = Path(lang_file)
        self._current_language: str = LANG_ENGLISH
        self._load_language()
    
    def _load_language(self) -> None:
        """Load language preference from file."""
        try:
            if self.lang_file.exists():
                with self.lang_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    lang = data.get("language", LANG_ENGLISH)
                    if lang in [LANG_ENGLISH, LANG_FARSI]:
                        self._current_language = lang
                        logger.info("Loaded language preference: %s from file: %s", lang, self.lang_file)
                    else:
                        logger.warning("Invalid language in file: %s, using default", lang)
            else:
                logger.info("Language file not found (%s), using default (English)", self.lang_file)
        except Exception as e:
            logger.error("Failed to load language preference from %s: %s", self.lang_file, e)
            self._current_language = LANG_ENGLISH
    
    def _save_language(self) -> None:
        """Save language preference to file."""
        try:
            self.lang_file.parent.mkdir(parents=True, exist_ok=True)
            with self.lang_file.open("w", encoding="utf-8") as f:
                json.dump({"language": self._current_language}, f, ensure_ascii=False, indent=2)
            logger.info("Saved language preference: %s (file: %s)", self._current_language, self.lang_file)
        except Exception as e:
            logger.error("Failed to save language preference: %s", e)
    
    def reload_language(self) -> None:
        """
        Reload language from file (useful if file was modified externally).
        
        This method can be called to reload the language preference from disk.
        """
        self._load_language()
    
    def get_language(self) -> str:
        """
        Get current language.
        
        Returns:
            Current language code ('en' or 'fa')
        """
        return self._current_language
    
    def set_language(self, lang: str) -> bool:
        """
        Set language preference.
        
        Args:
            lang: Language code ('en' or 'fa')
            
        Returns:
            True if language was set successfully, False if invalid
        """
        if lang not in [LANG_ENGLISH, LANG_FARSI]:
            logger.warning("Invalid language code: %s", lang)
            return False
        
        old_lang = self._current_language
        self._current_language = lang
        self._save_language()
        
        # Verify it was saved correctly
        if self._current_language != lang:
            logger.error("Language setting failed! Expected %s but got %s", lang, self._current_language)
            self._current_language = old_lang
            return False
        
        logger.info("Language changed from %s to %s", old_lang, lang)
        return True
    
    def translate(self, key: str, **kwargs: Any) -> str:
        """
        Translate a message key with optional parameters.
        
        Args:
            key: Translation key
            **kwargs: Parameters to format into translation
            
        Returns:
            Translated and formatted string, or key if translation not found
        """
        # Always use current language from instance (not cached)
        current_lang = self._current_language
        lang_dict = TRANSLATIONS.get(current_lang, TRANSLATIONS[LANG_ENGLISH])
        template = lang_dict.get(key, key)
        
        # Debug logging for language issues (can be removed after fixing)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("translate(key='%s', lang='%s') -> '%s'", key, current_lang, template[:50] + '...' if len(template) > 50 else template)
        
        # Log if we're using fallback
        if current_lang not in TRANSLATIONS:
            logger.warning("Language '%s' not in TRANSLATIONS, using English fallback", current_lang)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning("Missing parameter in translation '%s': %s", key, e)
            return template


# Global language manager instance
language_manager = LanguageManager()


def get_language() -> str:
    """Get current language."""
    return language_manager.get_language()


def set_language(lang: str) -> bool:
    """Set language."""
    return language_manager.set_language(lang)


def translate(key: str, **kwargs: Any) -> str:
    """Translate a message key."""
    return language_manager.translate(key, **kwargs)

