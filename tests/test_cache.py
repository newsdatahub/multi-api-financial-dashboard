import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from app.services.cache import CacheService
from app.config import config

@pytest.fixture
def cache_service(tmp_path):
    """Create a cache service with temporary directory."""
    # Override cache directory
    original_cache_dir = config.CACHE_DIR
    config.CACHE_DIR = tmp_path

    service = CacheService()

    yield service

    # Restore original
    config.CACHE_DIR = original_cache_dir

def test_cache_set_and_get(cache_service):
    """Test basic cache set and get operations."""
    data = {"ticker": "AAPL", "price": 150.0}

    cache_service.set("test", "AAPL", data)
    cached = cache_service.get_fresh("test", "AAPL")

    assert cached is not None
    assert cached["data"] == data
    assert "timestamp" in cached
    assert cached["source"] == "api"

def test_cache_miss_not_found(cache_service):
    """Test cache miss when file doesn't exist."""
    result = cache_service.get_fresh("nonexistent", "AAPL")
    assert result is None

def test_cache_age_formatting(cache_service):
    """Test that cache age is formatted correctly."""
    data = {"ticker": "AAPL", "price": 150.0}
    cache_service.set("test", "AAPL", data)

    age = cache_service.get_age("test", "AAPL")

    assert age is not None
    assert "ago" in age

def test_cache_fallback(cache_service, tmp_path):
    """Test fallback retrieval of stale cache."""
    # Create a stale cache file
    cache_path = tmp_path / "test_AAPL.json"
    old_timestamp = (datetime.now() - timedelta(hours=2)).isoformat()

    cache_data = {
        "data": {"ticker": "AAPL", "price": 150.0},
        "timestamp": old_timestamp,
        "source": "api"
    }

    with open(cache_path, "w") as f:
        json.dump(cache_data, f)

    # Regular get_fresh should return None (stale)
    result = cache_service.get_fresh("test", "AAPL")
    assert result is None

    # get_stale should return the stale data
    fallback = cache_service.get_stale("test", "AAPL")
    assert fallback is not None
    assert fallback["data"]["ticker"] == "AAPL"
    assert fallback["source"] == "fallback"
