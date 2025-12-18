from openai import AsyncOpenAI
from openai import APIError
from datetime import datetime
from app.config import config
from app.utils.logger import logger
from app.utils.retry import retry_with_backoff

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.session_calls = 0
        self.session_tokens = 0

    @retry_with_backoff(retry_on=(APIError,))
    async def generate_insights(self, ticker: str, price_data: dict, news_data: dict) -> dict:
        """Generate AI insights based on price and news data."""
        prompt = self._build_prompt(ticker, price_data, news_data)

        start_time = datetime.now()
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst assistant. Provide concise, "
                        "insightful analysis based on the provided stock data and news. "
                        "Focus on key trends, notable news impact, and relevant factors to watch. "
                        "Keep response under 100 words. Do not provide financial advice."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=210,
            temperature=0.7,
        )
        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        # Track usage
        usage = response.usage
        self.session_calls += 1
        self.session_tokens += usage.total_tokens

        logger.info(
            f"OPENAI | Call for {ticker} | "
            f"Tokens: {usage.prompt_tokens} prompt + {usage.completion_tokens} completion = {usage.total_tokens} total | "
            f"Response time: {elapsed:.0f}ms"
        )
        logger.info(
            f"OPENAI | Session total: {self.session_calls} calls | ~{self.session_tokens} tokens used"
        )

        return {
            "ticker": ticker,
            "insight": response.choices[0].message.content,
            "tokens_used": usage.total_tokens,
        }

    def _build_prompt(self, ticker: str, price_data: dict, news_data: dict) -> str:
        """Build prompt with price and news context."""
        # Price summary
        current = price_data.get("current_price", "N/A")
        previous = price_data.get("previous_close", "N/A")
        if current != "N/A" and previous != "N/A":
            change = ((current - previous) / previous) * 100
            price_summary = f"Current price: ${current:.2f} ({change:+.2f}% from previous close)"
        else:
            price_summary = "Price data unavailable"

        # News summary
        articles = news_data.get("articles", [])
        if articles:
            news_summary = "\n".join(
                f"- {a.get('title', 'Untitled')} ({a.get('source_title', 'Unknown')})" for a in articles[:5]
            )
        else:
            news_summary = "No recent news available"

        return f"""
Analyze {ticker} based on the following:

PRICE DATA:
{price_summary}

RECENT NEWS:
{news_summary}

Provide a brief analysis covering:
1. Current momentum and price action
2. Key news impact
3. Factors to watch
"""
