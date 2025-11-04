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

# Persian number formatting helper
def get_provider_name_persian(provider: str) -> str:
    """
    Get Persian name for a provider.
    
    Args:
        provider: Provider identifier (e.g., "wallex", "crawler2_alanchand", "crawler1_bonbast", "navasan")
        
    Returns:
        Persian provider name
    """
    provider_map = {
        "wallex": "ولکس",
        "crawler1_bonbast": "بن‌بست",
        "crawler2_alanchand": "الان‌چند",
        "navasan": "نوسان",
    }
    
    # Handle provider names that might have prefixes
    for key, persian_name in provider_map.items():
        if key in provider.lower():
            return persian_name
    
    # Default: return original if not found
    return provider


def format_persian_number(num: int) -> str:
    """
    Format number in Persian style: "X هزار و Y" or "X میلیون و Y هزار"
    
    Args:
        num: Integer to format
        
    Returns:
        Formatted Persian number string
    """
    if num < 1000:
        return str(num)
    
    if num < 1_000_000:
        thousands = num // 1000
        remainder = num % 1000
        if remainder == 0:
            return f"{thousands} هزار"
        else:
            return f"{thousands} هزار و {remainder}"
    
    millions = num // 1_000_000
    remainder = num % 1_000_000
    if remainder == 0:
        return f"{millions} میلیون"
    elif remainder < 1000:
        return f"{millions} میلیون و {remainder}"
    else:
        thousands = remainder // 1000
        remainder_hundreds = remainder % 1000
        if remainder_hundreds == 0:
            return f"{millions} میلیون و {thousands} هزار"
        else:
            return f"{millions} میلیون و {thousands} هزار و {remainder_hundreds}"


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
        "market_update_header": "New market fluctuation observed",
        "daily_report_header": "Daily price report:",
    },
    LANG_FARSI: {
        "usd_line": "دلار: {value}         {change}",
        "eur_line": "یورو : {value}          {change}",
        "gold_line": "طلا: {value}     {change}",
        "eurusd_line": "(یورو 💶) ۱ یورو  = ${value} (دلار 💵)  {change}",
        "tether_line": "(تتر 💎) ۱ تتر = {value} هزارتومان     {change_pct}% {arrow}",
        "time_elapsed": "مدت آرامش بازار: {elapsed}",
        "reported_by": "گزارش شده توسط {providers}",
        "no_data": "داده‌های بازار در دسترس نیست",
        "market_update_header": "نوسان جدید نبش بازار مشاهده شد",
        "daily_report_header": "گزارش روزانه قیمت‌ها:",
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
        # Default to Persian unless explicitly set
        from xrate.config import settings
        self._current_language: str = settings.default_language if hasattr(settings, 'default_language') else LANG_FARSI
        self._load_language()
    
    def _load_language(self) -> None:
        """Load language preference from file."""
        try:
            if self.lang_file.exists():
                with self.lang_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    lang = data.get("language", LANG_FARSI)  # Default to Persian
                    if lang in [LANG_ENGLISH, LANG_FARSI]:
                        self._current_language = lang
                        logger.info("Loaded language preference: %s from file: %s", lang, self.lang_file)
                    else:
                        logger.warning("Invalid language in file: %s, using default", lang)
            else:
                logger.info("Language file not found (%s), using default (Persian)", self.lang_file)
        except Exception as e:
            logger.error("Failed to load language preference from %s: %s", self.lang_file, e)
            # Default to Persian
            from xrate.config import settings
            self._current_language = settings.default_language if hasattr(settings, 'default_language') else LANG_FARSI
    
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


def translate_provider_name(provider: Optional[str]) -> str:
    """
    Translate provider name to current language.
    
    Args:
        provider: Provider identifier or None
        
    Returns:
        Translated provider name
    """
    if not provider:
        return "unknown"
    
    current_lang = language_manager.get_language()
    if current_lang == LANG_FARSI:
        return get_provider_name_persian(provider)
    else:
        # English: return original or map to readable name
        provider_map = {
            "wallex": "Wallex",
            "crawler1_bonbast": "Bonbast",
            "crawler2_alanchand": "AlanChand",
            "navasan": "Navasan",
        }
        for key, name in provider_map.items():
            if key in provider.lower():
                return name
        return provider

