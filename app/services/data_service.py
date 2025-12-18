from typing import Optional, Callable, Awaitable
import asyncio
from app.config import config
from app.services.cache import cache_service
from app.api.polygon import PolygonClient
from app.api.newsdatahub import NewsDataHubClient
from app.api.openai_client import OpenAIClient
from app.utils.logger import logger

class DataService:
    """
    Data service that orchestrates all data fetching operations with caching and fallback.

    This is the main orchestration layer that sits between the UI and the API clients.
    It implements resilient data fetching patterns including:

    Key responsibilities:
    - Orchestrate calls to multiple API clients (Polygon, NewsDataHub, OpenAI)
    - Implement intelligent caching strategy with fresh vs. stale data
    - Handle graceful degradation when APIs fail (fallback to stale cache)
    - Support two deployment modes:
      * Local mode: Fetches from APIs when cache is stale
      * Background refresh mode: Only reads from cache (never calls APIs)

    Architecture pattern:
    - Uses DRY principle with generic _fetch_with_cache() method
    - Eliminates 90+ lines of duplicate code across get_stock_data() and get_news()
    - All API clients have automatic retry logic via @retry_with_backoff decorator

    Flow:
    1. Check for fresh cached data (within TTL)
    2. If background mode: return stale cache or None
    3. If local mode: fetch from API with retry logic
    4. On API failure: fallback to stale cache
    5. Cache successful responses for future requests

    Usage:
        stock_data = await data_service.get_stock_data("NFLX")
        news_data = await data_service.get_news("NFLX")
        insights = await data_service.get_insights("NFLX", force_refresh=True)
    """
    def __init__(self):
        self.polygon = PolygonClient()
        self.news = NewsDataHubClient()
        self.openai = OpenAIClient()

    async def _fetch_with_cache(
        self,
        cache_type: str,
        cache_key: str,
        fetch_fn: Callable[[], Awaitable[dict]],
        error_prefix: str
    ) -> Optional[dict]:
        """
        Generic method to fetch data with caching and fallback.
        In background refresh mode, only reads from cache.

        Args:
            cache_type: Type of cache (e.g., 'polygon', 'news')
            cache_key: Cache key (usually ticker symbol)
            fetch_fn: Async function to fetch fresh data from API
            error_prefix: Prefix for error logging (e.g., 'POLYGON', 'NDH')
        """
        # Ensure this function always awaits something to remain a proper coroutine
        await asyncio.sleep(0)

        # Check cache first for fresh data
        cached = cache_service.get_fresh(cache_type, cache_key)
        if cached:
            return {
                **cached["data"],
                "data_age": cache_service.get_age(cache_type, cache_key),
                "is_fallback": False,
            }

        # In background refresh mode, use stale data as fallback
        if config.BACKGROUND_REFRESH:
            fallback = cache_service.get_stale(cache_type, cache_key)
            if fallback:
                return {
                    **fallback["data"],
                    "data_age": cache_service.get_age(cache_type, cache_key),
                    "is_fallback": True,
                }
            return None

        # Fetch from API
        try:
            data = await fetch_fn()
            cache_service.set(cache_type, cache_key, data)
            return {**data, "data_age": None, "is_fallback": False}

        except Exception as e:
            logger.error(f"{error_prefix} | Request failed | {cache_key} | {e}")

            # Try stale data as fallback on error
            fallback = cache_service.get_stale(cache_type, cache_key)
            if fallback:
                return {
                    **fallback["data"],
                    "data_age": cache_service.get_age(cache_type, cache_key),
                    "is_fallback": True,
                }
            return None

    async def get_stock_data(self, ticker: str) -> dict:
        """Get stock data with caching and fallback."""
        return await self._fetch_with_cache(
            cache_type="polygon",
            cache_key=ticker,
            fetch_fn=lambda: self.polygon.get_stock_data(ticker),
            error_prefix="POLYGON"
        )

    async def get_news(self, ticker: str) -> dict:
        """Get news with caching and fallback."""
        return await self._fetch_with_cache(
            cache_type="news",
            cache_key=ticker,
            fetch_fn=lambda: self.news.get_news(ticker),
            error_prefix="NDH"
        )

    async def get_insights(self, ticker: str, force_refresh: bool = False) -> dict:
        """
        Get AI insights with caching.
        Only regenerates on button click (force_refresh=True) in local mode.
        """
        cache_type = "insights"

        # Check cache (unless force refresh in local mode)
        if not force_refresh or config.BACKGROUND_REFRESH:
            cached = cache_service.get_stale(cache_type, ticker)  # Use stale data (no TTL check for insights)
            if cached:
                return {
                    **cached["data"],
                    "data_age": cache_service.get_age(cache_type, ticker),
                    "is_cached": True,
                }

        # In background refresh mode, we only show cached
        if config.BACKGROUND_REFRESH:
            return None

        # Generate new insights
        try:
            price_data = await self.get_stock_data(ticker)
            news_data = await self.get_news(ticker)

            if not price_data or not news_data:
                logger.warning(f"OPENAI | Cannot generate insights | Missing data for {ticker}")
                return None

            data = await self.openai.generate_insights(ticker, price_data, news_data)
            cache_service.set(cache_type, ticker, data)
            return {**data, "data_age": None, "is_cached": False}

        except Exception as e:
            logger.error(f"OPENAI | Request failed | {ticker} | {e}")
            return None

    async def get_related_stocks(self, ticker: str) -> dict:
        """Get related stocks data with caching."""
        cache_type = "related"
        cache_key = f"related_{ticker}"

        # Check cache first for fresh data
        cached = cache_service.get_fresh(cache_type, cache_key)
        if cached:
            return cached["data"]

        # In background refresh mode, use stale data as fallback
        if config.BACKGROUND_REFRESH:
            fallback = cache_service.get_stale(cache_type, cache_key)
            if fallback:
                return fallback["data"]
            return {}

        # Get related tickers for this stock
        related_tickers = config.RELATED_STOCKS.get(ticker, [])
        if not related_tickers:
            return {}

        # Fetch from API
        try:
            data = await self.polygon.get_related_stocks(related_tickers)
            if data:
                cache_service.set(cache_type, cache_key, data)
                return data
            else:
                # API returned empty - try stale cache before giving up
                fallback = cache_service.get_stale(cache_type, cache_key)
                if fallback:
                    return fallback["data"]
                return {}

        except Exception as e:
            logger.error(f"POLYGON | Related stocks request failed | {ticker} | {e}")

            # Try stale data as fallback on error
            fallback = cache_service.get_stale(cache_type, cache_key)
            if fallback:
                return fallback["data"]
            return {}

data_service = DataService()
