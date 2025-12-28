import httpx
import asyncio
from datetime import datetime, timedelta
from app.config import config
from app.utils.logger import logger
from app.utils.retry import retry_with_backoff

class PolygonClient:
    BASE_URL = "https://api.polygon.io"

    def __init__(self):
        self.api_key = config.POLYGON_API_KEY

    @retry_with_backoff(retry_on=(httpx.HTTPError,))
    async def get_stock_data(self, ticker: str) -> dict:
        """Fetch 1-month historical data for a ticker."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        url = f"{self.BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start_date:%Y-%m-%d}/{end_date:%Y-%m-%d}"
        params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc"}

        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            start_time = datetime.now()

            response = await client.get(url, params=params)
            response.raise_for_status()

            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            data = response.json()

            logger.info(
                f"POLYGON | Ticker: {ticker} | Response time: {elapsed:.0f}ms | "
                f"Data points: {len(data.get('results', []))}"
            )

            return self._transform_response(data, ticker)

    async def get_related_stocks(self, tickers: list) -> dict:
        """Fetch current data for related stocks in parallel."""
        @retry_with_backoff(retry_on=(httpx.HTTPError,))
        async def fetch_ticker(ticker: str):
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5)

                url = f"{self.BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start_date:%Y-%m-%d}/{end_date:%Y-%m-%d}"
                params = {"apiKey": self.api_key, "adjusted": "true", "sort": "desc"}

                async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    res = data.get("results", [])
                    if len(res) >= 2:
                        current = res[0]["c"]
                        previous = res[1]["c"]
                        change = current - previous
                        change_pct = (change / previous) * 100

                        return ticker, {
                            "current": current,
                            "change": change,
                            "change_pct": change_pct
                        }
                    else:
                        logger.warning(f"POLYGON | Insufficient data for {ticker} | Got {len(res)} data points, need 2")
                        return ticker, None
            except Exception as e:
                logger.warning(f"POLYGON | Failed to fetch {ticker} | {e}")
                return ticker, None

        # Fetch all tickers in parallel
        tasks = [fetch_ticker(ticker) for ticker in tickers]
        results_list = await asyncio.gather(*tasks)

        # Filter out failed fetches
        results = {ticker: data for ticker, data in results_list if data is not None}

        if len(results) == 0:
            logger.warning(f"POLYGON | Related stocks request failed | 0/{len(tickers)} successful")
        elif len(results) < len(tickers):
            logger.warning(f"POLYGON | Related stocks partially fetched | {len(results)}/{len(tickers)} successful")
        else:
            logger.info(f"POLYGON | Related stocks fetched | {len(results)}/{len(tickers)} successful")
        return results

    def _transform_response(self, data: dict, ticker: str) -> dict:
        """Transform API response to internal format."""
        results = data.get("results", [])

        # Calculate price range for chart y-axis with buffer
        price_range_min = None
        price_range_max = None
        if results:
            all_prices = [r["c"] for r in results]
            min_price = min(all_prices)
            max_price = max(all_prices)

            # Add buffer to min/max for better chart visualization
            price_range = max_price - min_price
            buffer = price_range * config.PRICE_CHART_BUFFER_PCT if price_range > 0 else max_price * config.PRICE_CHART_BUFFER_PCT
            price_range_min = min_price - buffer
            price_range_max = max_price + buffer

        return {
            "ticker": ticker,
            "prices": [
                {
                    "date": datetime.fromtimestamp(r["t"] / 1000).isoformat(),
                    "open": r["o"],
                    "high": r["h"],
                    "low": r["l"],
                    "close": r["c"],
                    "volume": r["v"],
                }
                for r in results
            ],
            "current_price": results[-1]["c"] if results else None,
            "previous_close": results[-2]["c"] if len(results) > 1 else None,
            "price_range_min": price_range_min,
            "price_range_max": price_range_max,
        }
