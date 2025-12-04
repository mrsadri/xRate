# src/xrate/application/stats.py
"""
Statistics Tracker - Track Bot Performance and Activity

This module tracks statistics about bot activity, including:
- Posts sent to channel
- Errors encountered
- Provider usage
- Time tracking

Files that USE this module:
- xrate.adapters.telegram.jobs (track posts and errors)
- xrate.adapters.telegram.handlers (track admin interactions)
- xrate.app (initialize stats and send summaries)

Files that this module USES:
- pathlib (file management)
- json (persistence)
- datetime (track timestamps)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Stats file path
STATS_FILE = Path("./data/stats.json")


@dataclass
class Feedback:
    """User feedback entry."""
    user_id: int
    username: str
    message: str
    timestamp: str  # ISO datetime string


@dataclass
class DailyStats:
    """Statistics for a single day."""
    date: str  # ISO date string (YYYY-MM-DD)
    posts_sent: int = 0
    errors_count: int = 0
    manual_posts: int = 0  # Posts via /post command
    provider_usage: Optional[Dict[str, int]] = None  # Provider name -> count
    crawler_usage: Optional[Dict[str, int]] = None  # Crawler name -> count (how many times used)
    last_post_time: Optional[str] = None  # ISO datetime string
    last_error_time: Optional[str] = None  # ISO datetime string
    feedback: list = None  # List of Feedback entries
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.provider_usage is None:
            self.provider_usage = {}
        if self.crawler_usage is None:
            self.crawler_usage = {}
        if self.feedback is None:
            self.feedback = []


@dataclass
class BotStats:
    """Overall bot statistics."""
    start_time: str  # ISO datetime string
    total_posts: int = 0
    total_errors: int = 0
    total_manual_posts: int = 0
    daily_stats: Dict[str, DailyStats] = None  # date -> DailyStats
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.daily_stats is None:
            self.daily_stats = {}


class StatsTracker:
    """Track and persist bot statistics."""
    
    def __init__(self, stats_file: Path = STATS_FILE):
        """
        Initialize stats tracker.
        
        Args:
            stats_file: Path to JSON file for persisting stats
        """
        self.stats_file = stats_file
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self._stats: Optional[BotStats] = None
        self._load_stats()
    
    def _load_stats(self) -> None:
        """Load statistics from disk."""
        if not self.stats_file.exists():
            self._stats = BotStats(
                start_time=datetime.now(timezone.utc).isoformat(),
            )
            logger.info("Initialized new stats tracker")
            return
        
        try:
            with self.stats_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convert daily_stats dict back to DailyStats objects
            daily_stats_dict = {}
            if "daily_stats" in data:
                for date, daily_data in data["daily_stats"].items():
                    # Convert feedback list to Feedback objects
                    feedback_list = []
                    if "feedback" in daily_data and daily_data["feedback"]:
                        for fb_data in daily_data["feedback"]:
                            feedback_list.append(Feedback(**fb_data))
                    daily_data["feedback"] = feedback_list
                    # Ensure crawler_usage exists for backward compatibility
                    if "crawler_usage" not in daily_data:
                        daily_data["crawler_usage"] = {}
                    daily_stats_dict[date] = DailyStats(**daily_data)
            
            self._stats = BotStats(
                start_time=data.get("start_time", datetime.now(timezone.utc).isoformat()),
                total_posts=data.get("total_posts", 0),
                total_errors=data.get("total_errors", 0),
                total_manual_posts=data.get("total_manual_posts", 0),
                daily_stats=daily_stats_dict,
            )
            logger.debug("Loaded stats from disk")
        except Exception as e:
            logger.error("Failed to load stats: %s", e)
            self._stats = BotStats(
                start_time=datetime.now(timezone.utc).isoformat(),
            )
    
    def _save_stats(self) -> None:
        """Save statistics to disk."""
        if not self._stats:
            return
        
        try:
            # Convert to JSON-serializable format
            data = {
                "start_time": self._stats.start_time,
                "total_posts": self._stats.total_posts,
                "total_errors": self._stats.total_errors,
                "total_manual_posts": self._stats.total_manual_posts,
                "daily_stats": {
                    date: {
                        **asdict(daily_stats),
                        "feedback": [asdict(fb) for fb in daily_stats.feedback]
                    }
                    for date, daily_stats in self._stats.daily_stats.items()
                },
            }
            
            with self.stats_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save stats: %s", e)
    
    def _get_today_stats(self) -> DailyStats:
        """Get or create today's statistics."""
        today = datetime.now(timezone.utc).date().isoformat()
        
        if today not in self._stats.daily_stats:
            self._stats.daily_stats[today] = DailyStats(date=today)
        
        return self._stats.daily_stats[today]
    
    def record_post(self, providers: Optional[list] = None, is_manual: bool = False) -> None:
        """
        Record a successful post to channel.
        
        Args:
            providers: List of provider names that were used
            is_manual: True if post was sent via /post command
        """
        if not self._stats:
            return
        
        self._stats.total_posts += 1
        if is_manual:
            self._stats.total_manual_posts += 1
        
        today = self._get_today_stats()
        today.posts_sent += 1
        if is_manual:
            today.manual_posts += 1
        today.last_post_time = datetime.now(timezone.utc).isoformat()
        
        # Track provider usage
        if providers:
            for provider in providers:
                today.provider_usage[provider] = today.provider_usage.get(provider, 0) + 1
        
        self._save_stats()
    
    def record_error(self, error_msg: Optional[str] = None) -> None:
        """
        Record an error.
        
        Args:
            error_msg: Optional error message
        """
        if not self._stats:
            return
        
        self._stats.total_errors += 1
        
        today = self._get_today_stats()
        today.errors_count += 1
        today.last_error_time = datetime.now(timezone.utc).isoformat()
        
        self._save_stats()
        logger.debug("Recorded error in stats: %s", error_msg)
    
    def record_feedback(self, user_id: int, username: str, message: str, timestamp: datetime) -> None:
        """
        Record user feedback for daily report.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            message: Feedback message text
            timestamp: When feedback was received
        """
        if not self._stats:
            return
        
        today = self._get_today_stats()
        feedback_entry = Feedback(
            user_id=user_id,
            username=username,
            message=message,
            timestamp=timestamp.isoformat(),
        )
        today.feedback.append(feedback_entry)
        self._save_stats()
        logger.debug("Recorded feedback from user %s (@%s)", user_id, username)
    
    def record_crawler_usage(self, crawler_name: str) -> None:
        """
        Record crawler usage (how many times a crawler was successfully used).
        
        Args:
            crawler_name: Name of the crawler (e.g., "crawler1_bonbast", "crawler2_alanchand")
        """
        if not self._stats:
            return
        
        today = self._get_today_stats()
        today.crawler_usage[crawler_name] = today.crawler_usage.get(crawler_name, 0) + 1
        self._save_stats()
        logger.debug("Recorded crawler usage: %s", crawler_name)
    
    def get_today_summary(self) -> Dict:
        """
        Get summary of today's activity.
        
        Returns:
            Dictionary with today's statistics
        """
        if not self._stats:
            return {}
        
        today = self._get_today_stats()
        return {
            "posts_sent": today.posts_sent,
            "errors_count": today.errors_count,
            "manual_posts": today.manual_posts,
            "provider_usage": today.provider_usage.copy(),
            "last_post_time": today.last_post_time,
            "last_error_time": today.last_error_time,
        }
    
    def get_last_24h_summary(self) -> Dict:
        """
        Get summary of last 24 hours activity.
        
        Returns:
            Dictionary with last 24 hours statistics
        """
        if not self._stats:
            return {}
        
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - 86400  # 24 hours ago
        
        posts_count = 0
        errors_count = 0
        manual_posts = 0
        provider_usage: Dict[str, int] = {}
        
        # Aggregate stats from all days that overlap with last 24h
        for date_str, daily_stats in self._stats.daily_stats.items():
            try:
                # Check if this day's last_post_time is within 24h
                if daily_stats.last_post_time:
                    post_time = datetime.fromisoformat(daily_stats.last_post_time.replace("Z", "+00:00"))
                    if post_time.timestamp() >= cutoff:
                        posts_count += daily_stats.posts_sent
                        errors_count += daily_stats.errors_count
                        manual_posts += daily_stats.manual_posts
                        for provider, count in daily_stats.provider_usage.items():
                            provider_usage[provider] = provider_usage.get(provider, 0) + count
            except Exception as e:
                logger.warning("Failed to process daily stats for %s: %s", date_str, e)
        
        # Aggregate crawler usage
        crawler_usage: Dict[str, int] = {}
        for date_str, daily_stats in self._stats.daily_stats.items():
            try:
                # Check if this day's last_post_time is within 24h
                if daily_stats.last_post_time:
                    post_time = datetime.fromisoformat(daily_stats.last_post_time.replace("Z", "+00:00"))
                    if post_time.timestamp() >= cutoff:
                        for crawler, count in daily_stats.crawler_usage.items():
                            crawler_usage[crawler] = crawler_usage.get(crawler, 0) + count
            except Exception as e:
                logger.warning("Failed to process crawler usage for %s: %s", date_str, e)
        
        return {
            "posts_sent": posts_count,
            "errors_count": errors_count,
            "manual_posts": manual_posts,
            "provider_usage": provider_usage,
            "crawler_usage": crawler_usage,
            "period": "24 hours",
        }
    
    def get_overall_stats(self) -> Dict:
        """
        Get overall statistics.
        
        Returns:
            Dictionary with overall statistics
        """
        if not self._stats:
            return {}
        
        return {
            "start_time": self._stats.start_time,
            "total_posts": self._stats.total_posts,
            "total_errors": self._stats.total_errors,
            "total_manual_posts": self._stats.total_manual_posts,
            "days_tracked": len(self._stats.daily_stats),
        }


# Global stats tracker instance
stats_tracker = StatsTracker()

