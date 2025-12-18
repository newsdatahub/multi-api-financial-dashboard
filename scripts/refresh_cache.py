"""
Background job to refresh cache for all tickers.
Run via cron: 0 */3 * * * /path/to/venv/python /path/to/refresh_cache.py
"""
import sys
import asyncio
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.api.polygon import PolygonClient
from app.api.newsdatahub import NewsDataHubClient
from app.api.openai_client import OpenAIClient
from app.services.cache import cache_service
from app.utils.logger import logger

async def refresh_ticker(ticker: str):
    """Refresh all data for a single ticker."""
    polygon = PolygonClient()
    news = NewsDataHubClient()
    openai = OpenAIClient()

    logger.info(f"REFRESH | Starting refresh for {ticker}")

    # Fetch stock data, news, and related stocks in parallel
    try:
        stock_data, news_data, related_data = await asyncio.gather(
            polygon.get_stock_data(ticker),
            news.get_news(ticker),
            polygon.get_related_stocks(config.RELATED_STOCKS.get(ticker, [])),
            return_exceptions=True
        )

        # Handle stock data
        if not isinstance(stock_data, Exception):
            cache_service.set("polygon", ticker, stock_data)
            logger.info(f"REFRESH | {ticker} | Stock data refreshed")
        else:
            logger.error(f"REFRESH | {ticker} | Stock data failed: {stock_data}")
            stock_data = None

        # Handle news data
        if not isinstance(news_data, Exception):
            cache_service.set("news", ticker, news_data)
            logger.info(f"REFRESH | {ticker} | News refreshed")
        else:
            logger.error(f"REFRESH | {ticker} | News failed: {news_data}")
            news_data = None

        # Handle related stocks data
        if not isinstance(related_data, Exception) and related_data:
            cache_service.set("related", f"related_{ticker}", related_data)
            logger.info(f"REFRESH | {ticker} | Related stocks refreshed")
        elif isinstance(related_data, Exception):
            logger.error(f"REFRESH | {ticker} | Related stocks failed: {related_data}")

        # Generate insights (only if we have both stock and news data)
        if stock_data and news_data:
            try:
                insights_data = await openai.generate_insights(ticker, stock_data, news_data)
                cache_service.set("insights", ticker, insights_data)
                logger.info(f"REFRESH | {ticker} | Insights refreshed")
            except Exception as e:
                logger.error(f"REFRESH | {ticker} | Insights failed: {e}")
        else:
            logger.warning(f"REFRESH | {ticker} | Skipping insights (missing data)")

    except Exception as e:
        logger.error(f"REFRESH | {ticker} | Unexpected error: {e}")

async def main():
    """Refresh all tickers in parallel."""
    logger.info("=" * 60)
    logger.info("REFRESH | Starting background refresh job")
    logger.info("=" * 60)

    # Refresh all tickers in parallel
    await asyncio.gather(*[refresh_ticker(ticker) for ticker in config.TICKERS])

    logger.info("=" * 60)
    logger.info("REFRESH | Background refresh complete")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
