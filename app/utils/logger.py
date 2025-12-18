import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config import config

def setup_logger() -> logging.Logger:
    """Configure and return the application logger."""

    # Create logs directory
    config.LOG_DIR.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("")
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        config.LOG_DIR / "app.log",
        maxBytes=config.LOG_FILE_MAX_BYTES,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

def log_startup():
    """Log application startup information."""
    logger.info("=" * 60)
    logger.info("STARTUP | Financial Dashboard")
    logger.info(f"STARTUP | Mode: {config.DEPLOYMENT_MODE}")
    logger.info(f"STARTUP | Background refresh: {config.BACKGROUND_REFRESH}")
    logger.info(f"STARTUP | Cache TTL: {config.CACHE_TTL_MINUTES} minutes")

    # Check API keys
    keys = {
        "POLYGON": bool(config.POLYGON_API_KEY),
        "NDH": bool(config.NEWSDATAHUB_API_KEY),
        "OPENAI": bool(config.OPENAI_API_KEY),
    }
    key_status = " | ".join(f"{k}: {'✓' if v else '✗'}" for k, v in keys.items())
    logger.info(f"STARTUP | API Keys: {key_status}")

    # Check cache directory
    cache_files = list(config.CACHE_DIR.glob("*.json")) if config.CACHE_DIR.exists() else []
    logger.info(f"STARTUP | Cache directory: {config.CACHE_DIR} ({len(cache_files)} files)")
    logger.info("=" * 60)
