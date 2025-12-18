import os
from pathlib import Path

class Config:
    # Deployment
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "local")
    BACKGROUND_REFRESH: bool = os.getenv("BACKGROUND_REFRESH", "false").lower() == "true"

    # Cache - with validation
    CACHE_TTL_MINUTES: int = max(1, int(os.getenv("CACHE_TTL_MINUTES", "10")))
    CACHE_MAX_AGE_HOURS: int = max(1, int(os.getenv("CACHE_MAX_AGE_HOURS", "24")))
    CACHE_DIR: Path = Path(__file__).parent.parent / "cache"

    # Background refresh - with validation
    REFRESH_INTERVAL_HOURS: int = max(1, int(os.getenv("REFRESH_INTERVAL_HOURS", "3")))

    # API Keys
    POLYGON_API_KEY: str = os.getenv("POLYGON_API_KEY", "")
    NEWSDATAHUB_API_KEY: str = os.getenv("NEWSDATAHUB_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(__file__).parent.parent / "logs"

    # App
    TICKERS: list = ["NFLX", "GOOGL", "TSLA"]
    TICKER_INFO: dict = {
        "NFLX": {"name": "Netflix", "exchange": "NASDAQ", "search_term": "Netflix", "brand_color": "#E50914"},
        "GOOGL": {"name": "Alphabet Inc.", "exchange": "NASDAQ", "search_term": "Google OR Alphabet", "brand_color": "#4285F4"},
        "TSLA": {"name": "Tesla Inc.", "exchange": "NASDAQ", "search_term": "Tesla", "brand_color": "#CC0000"},
        # Related stocks info
        "DIS": {"name": "Disney", "exchange": "NYSE"},
        "PARA": {"name": "Paramount", "exchange": "NASDAQ"},
        "WBD": {"name": "Warner Bros Discovery", "exchange": "NASDAQ"},
        "META": {"name": "Meta", "exchange": "NASDAQ"},
        "AMZN": {"name": "Amazon", "exchange": "NASDAQ"},
        "RIVN": {"name": "Rivian", "exchange": "NASDAQ"},
        "GM": {"name": "General Motors", "exchange": "NYSE"},
        "F": {"name": "Ford", "exchange": "NYSE"},
    }

    # Related stocks for each ticker
    RELATED_STOCKS: dict = {
        "NFLX": ["DIS", "PARA", "WBD"],
        "GOOGL": ["TSLA", "META", "AMZN"],
        "TSLA": ["RIVN", "GM", "F"],
    }

    # API Settings - with validation
    REQUEST_TIMEOUT: int = max(1, int(os.getenv("REQUEST_TIMEOUT", "10")))
    MAX_RETRIES: int = max(0, int(os.getenv("MAX_RETRIES", "3")))
    RETRY_BACKOFF_BASE: float = max(0.1, float(os.getenv("RETRY_BACKOFF_BASE", "0.5")))

    # News - with validation
    NEWS_FETCH_COUNT: int = max(1, int(os.getenv("NEWS_FETCH_COUNT", "100")))
    NEWS_DISPLAY_COUNT: int = max(1, int(os.getenv("NEWS_DISPLAY_COUNT", "5")))

    # UI Constants
    STREAMING_CHAR_DELAY: float = 0.01  # seconds per character for AI insights streaming effect
    PRICE_CHART_BUFFER_PCT: float = 0.10  # 10% buffer above/below price range for chart
    LOG_FILE_MAX_BYTES: int = 1_000_000  # 1MB max log file size

config = Config()
