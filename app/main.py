import streamlit as st
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from app.config import config
from app.services.data_service import data_service
from app.ui.components import (
    render_stock_info,
    render_price_chart,
    render_news_section,
    render_insights_section,
    render_data_age_indicator,
    render_related_stocks,
)
from app.utils.logger import logger, log_startup

# Page config
st.set_page_config(
    page_title="Financial Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Reduce top padding and add horizontal padding
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem !important;
    }
    @media (min-width: calc(736px + 8rem)) {
        .block-container {
            padding-left: 8rem !important;
            padding-right: 8rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize
if "initialized" not in st.session_state:
    try:
        log_startup()
    except Exception as e:
        st.error(f"Startup logging failed: {e}")
    st.session_state.initialized = True
    st.session_state.generate_insights = False

# Check API keys
if not config.POLYGON_API_KEY:
    st.error("⚠️ POLYGON_API_KEY not set in .env file")
if not config.NEWSDATAHUB_API_KEY:
    st.error("⚠️ NEWSDATAHUB_API_KEY not set in .env file")
if not config.OPENAI_API_KEY:
    st.error("⚠️ OPENAI_API_KEY not set in .env file")

# Main layout
col_main, col_sidebar = st.columns([3, 2])

with col_main:
    # Header and ticker selector on same line
    col_title, col_spacer, col_dropdown = st.columns([2, 1.2, 1.8])

    with col_title:
        st.markdown('<h1 style="color: #22c55e; white-space: nowrap;">Financial Dashboard</h1>', unsafe_allow_html=True)

    with col_dropdown:
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        ticker = st.selectbox(
            "Select stock",
            options=config.TICKERS,
            format_func=lambda t: f"{t} — {config.TICKER_INFO[t]['name']}",
            label_visibility="collapsed"
        )

# Render sections with individual loading states
with col_main:
    # Stock data section with its own loading
    stock_placeholder = st.empty()
    with stock_placeholder:
        with st.spinner("Loading stock data..."):
            try:
                stock_data = asyncio.run(data_service.get_stock_data(ticker))
            except Exception as e:
                logger.error(f"Failed to load stock data: {e}")
                stock_data = None

    stock_placeholder.empty()

    if stock_data:
        render_stock_info(ticker, stock_data)
        render_price_chart(stock_data)

        if stock_data.get("is_fallback"):
            render_data_age_indicator("Price", stock_data.get("data_age"))
    else:
        st.error("Unable to load stock data. Please try again later.")

    # Related stocks section with its own loading
    related_placeholder = st.empty()
    with related_placeholder:
        with st.spinner("Loading related stocks..."):
            try:
                related_data = asyncio.run(data_service.get_related_stocks(ticker))
            except Exception as e:
                logger.error(f"Failed to load related stocks: {e}")
                related_data = None

    related_placeholder.empty()

    if related_data:
        render_related_stocks(related_data)
    elif config.RELATED_STOCKS.get(ticker):
        st.markdown("### Related Stocks")
        st.info(f"Related stocks data unavailable for {ticker}")

with col_sidebar:
    # News section with its own loading
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### :green[Latest News]")

    news_placeholder = st.empty()
    with news_placeholder:
        with st.spinner("Loading news..."):
            try:
                news_data = asyncio.run(data_service.get_news(ticker))
            except Exception as e:
                logger.error(f"Failed to load news: {e}")
                news_data = None

    news_placeholder.empty()

    if news_data:
        render_news_section(news_data)
        if news_data.get("is_fallback"):
            render_data_age_indicator("News", news_data.get("data_age"))
    else:
        st.warning("News temporarily unavailable.")

    # AI Insights section
    render_insights_section(ticker, stock_data, news_data)
