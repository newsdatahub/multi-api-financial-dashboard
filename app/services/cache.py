import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any
from app.config import config
from app.utils.logger import logger

class CacheService:
    """
    Cache service for managing JSON-based file caching with TTL (Time To Live) support.

    This service implements a dual-strategy caching approach:
    - Fresh cache: Returns data only if within TTL (default: 10 minutes)
    - Stale cache: Returns data regardless of age (used as fallback when APIs fail)

    Key features:
    - JSON file-based storage for easy inspection and debugging
    - Automatic cleanup of files older than CACHE_MAX_AGE_HOURS (default: 24 hours)
    - Human-readable age formatting (e.g., "5m ago", "2h ago")
    - Timestamp tracking for all cached data

    Usage:
        cache_service.set("polygon", "NFLX", data)
        fresh_data = cache_service.get_fresh("polygon", "NFLX")  # None if stale
        fallback_data = cache_service.get_stale("polygon", "NFLX")  # Returns even if stale

    Cache file naming: {cache_type}_{ticker}.json
    Example: polygon_NFLX.json, news_GOOGL.json, insights_TSLA.json
    """
    def __init__(self):
        self.cache_dir = config.CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, cache_type: str, ticker: str) -> Path:
        """Get path for a cache file."""
        return self.cache_dir / f"{cache_type}_{ticker}.json"

    def get_fresh(self, cache_type: str, ticker: str) -> Optional[dict]:
        """
        Get cached data if fresh (within TTL).
        Returns None if cache doesn't exist or is stale.
        """
        cache_path = self._get_cache_path(cache_type, ticker)

        if not cache_path.exists():
            logger.debug(f"CACHE | Miss (not found) | {cache_type}_{ticker}")
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            timestamp = datetime.fromisoformat(cached["timestamp"])
            age = datetime.now() - timestamp
            age_minutes = age.total_seconds() / 60

            if age_minutes <= config.CACHE_TTL_MINUTES:
                logger.debug(
                    f"CACHE | Hit | {cache_type}_{ticker} | "
                    f"Age: {age_minutes:.1f}m"
                )
                return cached
            else:
                logger.debug(
                    f"CACHE | Miss (stale) | {cache_type}_{ticker} | "
                    f"Age: {age_minutes:.1f}m > TTL: {config.CACHE_TTL_MINUTES}m"
                )
                return None

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"CACHE | Corrupted file | {cache_type}_{ticker} | {e}")
            return None

    def get_stale(self, cache_type: str, ticker: str) -> Optional[dict]:
        """
        Get cached data regardless of age (stale data OK for fallback).
        Returns None only if cache doesn't exist.
        """
        cache_path = self._get_cache_path(cache_type, ticker)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            age = datetime.now() - datetime.fromisoformat(cached["timestamp"])
            logger.info(
                f"CACHE | Fallback used | {cache_type}_{ticker} | "
                f"Age: {self._format_age(age)}"
            )
            cached["source"] = "fallback"
            return cached

        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, cache_type: str, ticker: str, data: Any) -> None:
        """Save data to cache."""
        cache_path = self._get_cache_path(cache_type, ticker)

        cached = {
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": "api",
        }

        with open(cache_path, "w") as f:
            json.dump(cached, f, indent=2)

        logger.debug(f"CACHE | Write | {cache_type}_{ticker}")

        # Cleanup old files on write
        self._cleanup()

    def get_age(self, cache_type: str, ticker: str) -> Optional[str]:
        """Get human-readable age of cached data."""
        cache_path = self._get_cache_path(cache_type, ticker)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            timestamp = datetime.fromisoformat(cached["timestamp"])
            age = datetime.now() - timestamp
            return self._format_age(age)

        except (json.JSONDecodeError, KeyError):
            return None

    def _format_age(self, age: timedelta) -> str:
        """Format timedelta as human-readable string."""
        total_seconds = int(age.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"

    def _cleanup(self) -> None:
        """Delete cache files older than CACHE_MAX_AGE_HOURS."""
        cutoff = datetime.now() - timedelta(hours=config.CACHE_MAX_AGE_HOURS)
        deleted = 0

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)

                timestamp = datetime.fromisoformat(cached["timestamp"])
                if timestamp < cutoff:
                    cache_file.unlink()
                    deleted += 1

            except (json.JSONDecodeError, KeyError, OSError):
                # If we can't read it, delete it
                cache_file.unlink()
                deleted += 1

        if deleted > 0:
            logger.info(f"CACHE | Cleanup | Deleted {deleted} stale files")

cache_service = CacheService()
