import httpx
from datetime import datetime
from app.config import config
from app.utils.logger import logger
from app.utils.retry import retry_with_backoff

class NewsDataHubClient:
    BASE_URL = "https://api.newsdatahub.com/v1"

    def __init__(self):
        self.api_key = config.NEWSDATAHUB_API_KEY
        self.quota_remaining = None
        self.quota_limit = None
        self.quota_reset = None

    @retry_with_backoff(retry_on=(httpx.HTTPError,))
    async def get_news(self, ticker: str) -> dict:
        """Fetch news articles for a ticker using company name search."""
        # Get the search term for this ticker (company name instead of ticker symbol)
        search_term = config.TICKER_INFO.get(ticker, {}).get("search_term", ticker)

        url = f"{self.BASE_URL}/news"
        base_params = {
            "language": "en",
            "topic": "business,economy,finance",
            "start_date": "2025-12-01",
            "q": search_term,
            "search_in": "title",
            "sort_by": "date",
            "per_page": config.NEWS_FETCH_COUNT,
        }
        headers = {"x-api-key": self.api_key}

        all_articles = []

        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            # Fetch page 1
            start_time = datetime.now()
            params = base_params.copy()
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            all_articles.extend(data.get("data", []))
            next_cursor = data.get("next_cursor")

            # Fetch page 2 if cursor exists
            if next_cursor:
                params["cursor"] = next_cursor
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                all_articles.extend(data.get("data", []))

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            # Extract quota headers from last response
            self._update_quota_from_headers(response.headers)

            articles = self._deduplicate_articles(all_articles, search_term)

            logger.info(
                f"NDH | Quota: {self.quota_limit - self.quota_remaining}/{self.quota_limit} used | "
                f"Remaining: {self.quota_remaining} | "
                f"Ticker: {ticker} (search: '{search_term}') | "
                f"Pages: 2 | Response time: {elapsed:.0f}ms"
            )
            logger.info(
                f"NDH | Dedup: {len(all_articles)} fetched → "
                f"{len(articles)} after dedup"
            )

            return {"ticker": ticker, "articles": articles[:config.NEWS_DISPLAY_COUNT]}

    def _update_quota_from_headers(self, headers: dict):
        """Extract rate limit info from response headers."""
        self.quota_limit = int(headers.get("X-RateLimit-Limit", 100))
        self.quota_remaining = int(headers.get("X-RateLimit-Remaining", 0))
        self.quota_reset = headers.get("X-RateLimit-Reset")

        if self.quota_remaining < 20:
            logger.warning(
                f"NDH | Quota low: {self.quota_limit - self.quota_remaining}/{self.quota_limit} used | "
                f"Resets: {self.quota_reset}"
            )

    def _deduplicate_articles(self, articles: list, search_term: str = "") -> list:
        """
        Deduplicate articles:
        1. Filter for relevance (search term must be in title)
        2. Remove duplicate headlines (keep first/freshest)
        3. Keep up to 2 articles per source (freshest ones)
        """
        # Step 1: Filter for relevance - search term must appear in title
        relevant_articles = []
        for article in articles:
            title = article.get("title", "").lower()

            # Check if any part of the search term appears in title
            # Handle OR queries like "Google OR Alphabet"
            search_terms = [term.strip().lower() for term in search_term.split(" OR ")]

            if any(term in title for term in search_terms):
                relevant_articles.append(article)

        logger.debug(f"NDH | Relevance filter: {len(articles)} → {len(relevant_articles)} relevant")

        # Step 2: Remove duplicate headlines
        seen_headlines = set()
        unique_headlines = []
        for article in relevant_articles:
            headline = article.get("title", "").lower().strip()
            if headline not in seen_headlines:
                seen_headlines.add(headline)
                unique_headlines.append(article)

        # Step 2: Keep up to 2 articles per source (freshest ones)
        source_articles = {}
        for article in unique_headlines:
            source = article.get("source_title", "unknown")
            if source not in source_articles:
                source_articles[source] = []
            source_articles[source].append(article)

        # For each source, keep up to 2 freshest articles
        result = []
        for source, source_list in source_articles.items():
            # Sort by date descending and take top 2
            sorted_articles = sorted(source_list, key=lambda x: x.get("pub_date", ""), reverse=True)
            result.extend(sorted_articles[:2])

        # Sort final result by date descending (freshest first)
        result = sorted(result, key=lambda x: x.get("pub_date", ""), reverse=True)

        logger.debug(
            f"NDH | Dedup details: {len(articles)} → "
            f"{len(unique_headlines)} after headline dedup → "
            f"{len(result)} after source dedup (up to 2 per source)"
        )

        return result
