import asyncio
import functools
from typing import Tuple, Type
from app.config import config
from app.utils.logger import logger

def retry_with_backoff(
    max_retries: int = None,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator that intercepts API errors and retries with intelligent backoff.

    Retry Strategy:
    - Transient errors (timeouts, 500s): Quick backoff (0.5s → 1s → 2s)
    - Rate limits (429): Longer delays (15s per attempt)
    - Client errors (4xx except 429): No retry

    After all retries fail, calling code can fall back to stale cache.
    """
    if max_retries is None:
        max_retries = config.MAX_RETRIES

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    # Check if we should retry
                    if not _should_retry(e):
                        raise

                    if attempt < max_retries:
                        delay = _get_retry_delay(e, attempt, config.RETRY_BACKOFF_BASE)

                        # Special logging for rate limits
                        error_type = "Rate limit (429)" if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429 else str(e)

                        logger.warning(
                            f"RETRY | {func.__name__} | Attempt {attempt + 1}/{max_retries + 1} | "
                            f"Error: {error_type} | Backing off {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"RETRY | {func.__name__} | All {max_retries + 1} attempts failed | "
                            f"Last error: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator

def _should_retry(exception: Exception) -> bool:
    """Determine if an exception warrants a retry."""
    import httpx

    # Always retry network errors
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
        return True

    # Check HTTP status codes
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        # Retry on 429 (rate limit) and 5xx (server errors)
        if status == 429 or status >= 500:
            return True
        # Don't retry on other 4xx
        return False

    # Default: retry on unknown exceptions
    return True

def _get_retry_delay(exception: Exception, attempt: int, base_delay: float) -> float:
    """
    Calculate retry delay based on exception type and attempt number.

    For 429 rate limits (e.g., Polygon's 5 calls/minute):
    - Retry 1: 15s delay
    - Retry 2: 30s delay
    - Retry 3: 45s delay
    Total: 90s for all retries

    For other transient errors (timeouts, 5xx):
    - Standard exponential backoff: 0.5s, 1s, 2s
    """
    import httpx

    # For 429 (rate limit), use longer delays to respect API quotas
    if isinstance(exception, httpx.HTTPStatusError) and exception.response.status_code == 429:
        # Polygon has 5 calls/minute (one call every 12s)
        # Wait 15s between retries to avoid burning through quota
        return 15 * (attempt + 1)

    # For other errors, use standard exponential backoff
    return base_delay * (2 ** attempt)
