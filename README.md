# Multi-API Financial Dashboard

A Streamlit dashboard demonstrating resilient patterns for integrating multiple APIs with caching, retry logic, and graceful error handling.

![Streamlit](https://img.shields.io/badge/streamlit-v1.29+-brightgreen) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Overview

This financial dashboard aggregates real-time stock data, news articles, and AI-generated insights for Netflix (NFLX), Alphabet (GOOGL), and Tesla (TSLA). You'll build a working dashboard and learn how to prevent unpredictable API costs in case you choose to deploy this application to production. When `BACKGROUND_REFRESH=true`, the Streamlit app serves only from cache and never calls external APIs—a separate scheduled job refreshes the cache at fixed intervals, decoupling API quota consumption from user traffic volume.

**Disclaimer:** This application is for educational and demonstration purposes only. It does not provide financial, investment, legal, or professional advice. Stock data and AI-generated insights should not be used as the basis for any investment decisions. Always consult with qualified financial professionals before making investment decisions. The developers are not responsible for any financial losses or damages resulting from the use of this application.

The application showcases:

- **Multi-API integration** with Polygon.io, NewsDataHub, and OpenAI
- **Smart caching** with configurable TTL and stale data fallback
- **Retry logic** with exponential backoff for network failures and rate limits
- **Graceful degradation** when APIs are unavailable
- **DRY refactoring** with generic cache handling
- **Mobile-responsive UI** with dark theme

## Features

### Data Sources
- **Stock Prices** - Real-time pricing and 1-month historical charts with dynamic y-axis scaling via [Polygon.io API](https://polygon.io)
- **Related Stocks** - Competitor stock prices with daily percentage changes
- **News Articles** - Curated financial news from mainstream sources (5 articles displayed, with 3-step deduplication: relevance → headline → source) via [NewsDataHub API](https://newsdatahub.com)
- **AI Insights** - GPT-powered analysis combining price trends and news via [OpenAI API](https://openai.com)

### Technical Highlights
- **Independent component loading** - Each UI section (stock data, news, related stocks) renders independently with separate loading states
- **Async API calls** - Non-blocking HTTP requests using httpx.AsyncClient and asyncio.gather() for parallel fetching
- **Retry decorator with intelligent backoff** - Handles transient failures (429s with 15s/30s/45s delays, 5xx/timeouts with 0.5s/1s/2s delays)
- **Smart caching** with fresh vs. stale data strategies (`get_fresh()` and `get_stale()` methods)
- **Refactored data service** using generic `_fetch_with_cache()` method (DRY principle)
- **JSON-based file caching** with automatic cleanup
- **Comprehensive logging** with rotation
- **Dynamic chart scaling** based on actual price range
- **Brand color customization** - Tickers display in company brand colors
- **Two deployment modes** (local interactive / VPS background refresh)

## Resilient Design Patterns

### 1. Retry Logic with Intelligent Backoff

All API clients use the `@retry_with_backoff` decorator to handle transient failures and rate limits:

```python
@retry_with_backoff(retry_on=(httpx.HTTPError,))
async def get_stock_data(self, ticker: str) -> dict:
    # API call with automatic retry on:
    # - 429 (rate limit exceeded) → 15s, 30s, 45s delays
    # - 5xx (server errors) → 0.5s, 1s, 2s delays
    # - Network timeouts → 0.5s, 1s, 2s delays
    # - Does NOT retry on 4xx client errors (except 429)
```

**Implementation details:**
- HTTP status codes trigger different retry behavior: 429 and 5xx retry, 4xx (except 429) do not
- 429 errors use 15s/30s/45s delays (total 90s) to respect Polygon's 5 calls/minute quota
- Other retryable errors (5xx, timeouts) use 0.5s/1s/2s exponential backoff (total 3.5s)
- Implemented as Python decorator applied to async methods in API client classes
- Retries on actual failures instead of preemptively rate limiting (simpler, more responsive)

The `DataService` uses a single `_fetch_with_cache()` method instead of duplicating logic:

```python
async def _fetch_with_cache(self, cache_type, cache_key, fetch_fn, error_prefix):
    # 1. Check for fresh cached data
    # 2. Fall back to stale data if in background mode
    # 3. Fetch from API with retry
    # 4. Fall back to stale data on error

# Simple usage:
async def get_stock_data(self, ticker: str) -> dict:
    return await self._fetch_with_cache(
        cache_type="polygon",
        cache_key=ticker,
        fetch_fn=lambda: self.polygon.get_stock_data(ticker),
        error_prefix="POLYGON"
    )
```

**Result:**
- Reduced code duplication by 90+ lines (get_stock_data and get_news previously duplicated caching logic)
- Caching logic exists in one location (_fetch_with_cache method)
- Changes to caching behavior require updates in one place
- Retry logic remains in API client methods via @retry_with_backoff decorator

### 2. Fresh vs. Stale Cache Strategy

The cache service implements two retrieval methods with different TTL enforcement:

- **`get_fresh()`** - Returns cached data only if timestamp age < CACHE_TTL_MINUTES (10 minutes default), otherwise returns None
- **`get_stale()`** - Returns cached data regardless of timestamp age, used when API calls fail

When all API retries fail, DataService calls get_stale() to return expired cache instead of failing completely.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Application                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │     UI      │  │   Services  │  │      API Clients        │  │
│  │  Components │◄─┤  (Cache,    │◄─┤  (Polygon, NDH, OpenAI) │  │
│  │             │  │   Data)     │  │  [@retry_with_backoff]  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Cache Layer                               │
│         (JSON Files: get_fresh() vs. get_stale() data)           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────┬───────────────────┬─────────────────────────┐
│   Polygon API     │  NewsDataHub API  │      OpenAI API         │
│   (Stock Data)    │     (News)        │    (AI Insights)        │
└───────────────────┴───────────────────┴─────────────────────────┘
```

## Prerequisites

- **Python 3.9+**
- **API Keys** (all free tiers available):
  - [Polygon.io](https://polygon.io) - Stock market data
  - [NewsDataHub](https://newsdatahub.com) - News articles
  - [OpenAI](https://platform.openai.com) - AI insights

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/multi-api-financial-dashboard.git
cd multi-api-financial-dashboard
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# API Keys (required)
POLYGON_API_KEY=your_polygon_api_key_here
NEWSDATAHUB_API_KEY=your_newsdatahub_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Cache Configuration (optional)
CACHE_TTL_MINUTES=10
LOG_LEVEL=INFO
```

## Running the Application

### Start the Dashboard

```bash
streamlit run app/main.py
```

The application will open in your browser at `http://localhost:8501`.

### Using the Dashboard

1. **Select a stock** from the dropdown (NFLX, GOOGL, or TSLA)
2. **View real-time price** with percentage change
3. **Explore the price chart** showing 1-month history with dynamic y-axis scaling
4. **See related stocks** below the chart (e.g., DIS, PARA, WBD for NFLX)
5. **Read latest news** from mainstream sources (5 articles in scrollable view)
6. **Generate AI insights** by clicking the button (concise 100-word analysis)

### Cache Behavior

On first load, the app fetches fresh data from all APIs. Subsequent requests within the cache TTL (default: 10 minutes) are served from cache, avoiding unnecessary API calls.

You'll see cache age indicators when viewing cached data:

```
⏱️ Price data from 5m ago
```

## Background Refresh Mode (Optional)

**Purpose:** Prevent unpredictable API quota usage when deploying to production.

### How It Works

The application supports two modes controlled by the `BACKGROUND_REFRESH` environment variable:

**Local Mode** (`BACKGROUND_REFRESH=false`, default):
- User requests trigger the following logic in `DataService._fetch_with_cache()`:
  1. Check if cached data exists and is fresh (age < `CACHE_TTL_MINUTES`)
  2. If fresh: return cached data
  3. If stale or missing: call external API, cache response, return data
  4. If API call fails: return stale cached data as fallback
- API quota consumption scales with user traffic volume

**Background Refresh Mode** (`BACKGROUND_REFRESH=true`):
- User requests trigger the following logic in `DataService._fetch_with_cache()`:
  1. Check if cached data exists and is fresh (age < `CACHE_TTL_MINUTES`)
  2. If fresh: return cached data
  3. If stale or missing: return stale cached data (API is **never** called)
- A separate process (`scripts/refresh_cache.py`) runs on a fixed schedule (e.g., cron job every 3 hours)
- This background job calls external APIs and updates cache files
- API quota consumption is constant regardless of user traffic volume

### Configuration

Set in your `.env` file:
```env
BACKGROUND_REFRESH=true
```

Run the background refresh job via cron (example for every 3 hours):
```bash
0 */3 * * * /path/to/venv/bin/python /path/to/scripts/refresh_cache.py
```

### When to Use

- **Local Mode:** Development, testing, personal use
- **Background Mode:** Production deployments where you need predictable API costs

**Tradeoff:** In background mode, data can be up to 3 hours stale (based on refresh interval), but users get instant responses and your API quota usage remains constant.

## Testing

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage Report

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test Files

```bash
# Test configuration
pytest tests/test_config.py

# Test caching
pytest tests/test_cache.py

# Test API clients
pytest tests/test_polygon.py
pytest tests/test_newsdatahub.py
```

### Expected Coverage

The test suite achieves approximately **25-30% coverage**, focusing on:

- ✅ Configuration management with validation
- ✅ Cache operations (set, get_fresh, get_stale, cleanup)
- ✅ API response transformations
- ✅ News deduplication logic

## Project Structure

```
multi-api-financial-dashboard/
├── app/
│   ├── main.py                     # Streamlit entry point
│   ├── config.py                   # Configuration with validation
│   ├── api/
│   │   ├── polygon.py              # Polygon API client [@retry_with_backoff]
│   │   ├── newsdatahub.py          # NewsDataHub API client [@retry_with_backoff]
│   │   └── openai_client.py        # OpenAI API client [@retry_with_backoff]
│   ├── services/
│   │   ├── cache.py                # Cache service (get_fresh/get_stale methods)
│   │   └── data_service.py         # Orchestration with _fetch_with_cache
│   ├── ui/
│   │   └── components.py           # Reusable UI components
│   └── utils/
│       ├── logger.py               # Logging configuration
│       └── retry.py                # @retry_with_backoff decorator (429-aware)
├── scripts/
│   └── refresh_cache.py            # Background refresh job
├── tests/                          # Test suite
├── cache/                          # JSON cache files (git-ignored)
├── logs/                           # Log files (git-ignored)
├── .streamlit/
│   └── config.toml                 # Streamlit theme configuration
├── .env.example                    # Environment variables template
├── requirements.txt                # Python dependencies
└── README.md
```

## Configuration Options

All configuration is managed through environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOYMENT_MODE` | `local` | Deployment identifier |
| `BACKGROUND_REFRESH` | `false` | If true, app only reads cache |
| `CACHE_TTL_MINUTES` | `10` | Cache freshness duration |
| `CACHE_MAX_AGE_HOURS` | `24` | Delete cache files older than this |
| `POLYGON_API_KEY` | — | Polygon.io API key (required) |
| `NEWSDATAHUB_API_KEY` | — | NewsDataHub API key (required) |
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Logging

Logs are written to both console and `logs/app.log` with automatic rotation (max 1MB per file, 5 backups).

### Log Format

```
2024-12-15 10:32:15 | INFO  | POLYGON | Call 1/5 | Ticker: AAPL | Response time: 234ms | Data points: 30
2024-12-15 10:32:16 | DEBUG | CACHE | Hit | news_AAPL | Age: 4.2m
2024-12-15 10:32:20 | INFO  | OPENAI | Call for AAPL | Tokens: 610 total | Response time: 1842ms
```

### Log Levels

- **DEBUG** - Cache hits/misses, rate limiter details
- **INFO** - API calls, response times, quota usage
- **WARNING** - Rate limits reached, low quota, stale cache
- **ERROR** - API failures, network errors

## API Error Handling

The application handles API failures gracefully:

### Retry Strategy

All API calls automatically retry on transient failures with intelligent backoff:

| Error Type | Retry Delays | Total Wait | Rationale |
|------------|-------------|------------|-----------|
| **429 (Rate Limit)** | 15s, 30s, 45s | 90s | Respects Polygon's 5 calls/min quota (12s per call) |
| **5xx (Server Errors)** | 0.5s, 1s, 2s | 3.5s | Fast recovery from transient server issues |
| **Network Timeouts** | 0.5s, 1s, 2s | 3.5s | Quick retry for connectivity problems |
| **4xx (Client Errors)** | No retry | 0s | Permanent errors (except 429) |

### Cache Fallback

If all retries fail, the app serves stale cached data:
```
⏱️ Price data from 2h ago  ← Stale data indicator
```

This ensures the dashboard remains functional even during API outages.

## Troubleshooting

### Application won't start

- **Check API keys** - Ensure all three API keys are set in `.env`
- **Check Python version** - Requires Python 3.9+
- **Reinstall dependencies** - Run `pip install -r requirements.txt`

### No data showing

- **Check logs** - Look at `logs/app.log` for errors
- **Verify API keys** - Test keys are valid and have quota remaining
- **Check network** - Ensure you can reach external APIs

### Tests failing

- **Install test dependencies** - Ensure pytest is installed
- **Check permissions** - Tests create temp directories
- **Run with verbose mode** - Use `pytest -v` for detailed output

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Resources

- **APIs**
  - [Polygon.io Documentation](https://polygon.io/docs)
  - [NewsDataHub API Documentation](https://newsdatahub.com/docs)
  - [OpenAI API Documentation](https://platform.openai.com/docs)
- **Technologies**
  - [Streamlit Documentation](https://docs.streamlit.io)
  - [Plotly Python Documentation](https://plotly.com/python/)
  - [httpx Documentation](https://www.python-httpx.org/)

## Support

For issues or questions:
- Open an issue on GitHub
- Check the logs in `logs/app.log`
- Review the API documentation links above
