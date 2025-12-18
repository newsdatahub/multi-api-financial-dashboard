import os
import pytest
from app.config import Config

def test_config_defaults():
    """Test that config has correct default values."""
    config = Config()

    assert config.DEPLOYMENT_MODE == "local"
    assert config.BACKGROUND_REFRESH == False
    assert config.CACHE_TTL_MINUTES == 10
    assert config.MAX_RETRIES == 3
    assert config.TICKERS == ["NFLX", "GOOGL", "TSLA"]

def test_config_tickers():
    """Test that all tickers have info."""
    config = Config()

    for ticker in config.TICKERS:
        assert ticker in config.TICKER_INFO
        assert "name" in config.TICKER_INFO[ticker]
        assert "exchange" in config.TICKER_INFO[ticker]

def test_config_env_override(monkeypatch):
    """Test that environment variables can be read by Config class."""
    # Set env vars before importing/creating config
    monkeypatch.setenv("CACHE_TTL_MINUTES", "180")
    monkeypatch.setenv("MAX_RETRIES", "5")

    # Create new config instance that will read these env vars
    import importlib
    from app import config as config_module
    importlib.reload(config_module)

    # Test that config reads from environment
    assert config_module.config.CACHE_TTL_MINUTES == 180
    assert config_module.config.MAX_RETRIES == 5

    # Reload again to restore defaults
    importlib.reload(config_module)
