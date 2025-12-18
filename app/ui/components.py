import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import asyncio
import time
from datetime import datetime
from app.config import config
from app.services.data_service import data_service

def render_header() -> str:
    """Render header with logo and ticker selector. Returns selected ticker."""
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("# Stock*Pulse*")

        ticker = st.selectbox(
            "Select stock",
            options=config.TICKERS,
            format_func=lambda t: f"{t} — {config.TICKER_INFO[t]['name']}",
        )

    return ticker

def render_stock_info(ticker: str, stock_data: dict):
    """Render ticker name and price with delta."""
    info = config.TICKER_INFO[ticker]
    current_price = stock_data.get("current_price")
    previous_close = stock_data.get("previous_close")
    brand_color = info.get("brand_color", "#22c55e")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown(f'<h2 style="color: {brand_color};">{ticker}</h2>', unsafe_allow_html=True)
        st.caption(f"{info['name']} · {info['exchange']}")

    with col2:
        if current_price and previous_close:
            delta = current_price - previous_close
            delta_pct = (delta / previous_close) * 100
            st.metric(
                label="Price",
                value=f"${current_price:,.2f}",
                delta=f"{delta:+.2f} ({delta_pct:+.2f}%)",
            )
        elif current_price:
            st.metric(label="Price", value=f"${current_price:,.2f}")

def render_price_chart(stock_data: dict):
    """Render interactive price chart using Plotly."""
    prices = stock_data.get("prices", [])

    if not prices:
        st.warning("No price data available for chart.")
        return

    # Convert to pandas for better date handling
    dates = pd.to_datetime([p["date"] for p in prices])
    closes = [p["close"] for p in prices]

    fig = go.Figure()

    # Area fill with straight lines
    fig.add_trace(go.Scatter(
        x=dates,
        y=closes,
        fill="tozeroy",
        fillcolor="rgba(34, 197, 94, 0.1)",
        line=dict(color="#22c55e", width=2),
        mode="lines+markers",
        marker=dict(size=4, color="#22c55e"),
        name="Price",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
        connectgaps=False,
    ))

    # Configure y-axis range based on data
    yaxis_config = dict(
        gridcolor="rgba(255,255,255,0.1)",
        tickprefix="$",
    )

    # Set custom range if available
    price_range_min = stock_data.get("price_range_min")
    price_range_max = stock_data.get("price_range_max")
    if price_range_min is not None and price_range_max is not None:
        yaxis_config["range"] = [price_range_min, price_range_max]

    fig.update_layout(
        title="Price History (1 Month)",
        xaxis_title="",
        yaxis_title="",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        height=350,
        showlegend=False,
        hovermode="x unified",
        yaxis=yaxis_config,
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.1)",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

def render_news_section(news_data: dict):
    """Render news articles."""
    articles = news_data.get("articles", [])

    if not articles:
        st.info("No recent news available.")
        return

    # Apply link styling and reduce spacing
    st.markdown(
        """
        <style>
        div[data-testid="stMarkdownContainer"] a {
            color: #fafafa !important;
            text-decoration: none !important;
        }
        div[data-testid="stMarkdownContainer"] a:hover {
            color: #22c55e !important;
        }
        div[data-testid="stMarkdownContainer"] p {
            margin-bottom: 0.2rem !important;
        }
        div[data-testid="stCaptionContainer"] {
            margin-top: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    for article in articles:
        title = article.get("title", "Untitled")
        source = article.get("source_title", "Unknown")
        pub_date = article.get("pub_date", "")
        url = article.get("article_link", article.get("url", ""))

        # Format date
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                age = datetime.now(dt.tzinfo) - dt
                if age.days > 0:
                    time_ago = f"{age.days}d ago"
                elif age.seconds >= 3600:
                    time_ago = f"{age.seconds // 3600}h ago"
                else:
                    time_ago = f"{age.seconds // 60}m ago"
            except Exception:
                time_ago = ""
        else:
            time_ago = ""

        # Render article
        if url:
            st.markdown(f"**[{title}]({url})**")
        else:
            st.markdown(f"**{title}**")

        st.caption(f"{source} · {time_ago}")

def render_insights_section(ticker: str, stock_data: dict, news_data: dict):
    """Render AI insights with generate button."""
    # Header with button on same line
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### :green[AI Insights]")
    with col2:
        generate_clicked = st.button("Generate", key="insights_btn")

    # Check for cached insights
    insights_data = asyncio.run(data_service.get_insights(ticker, force_refresh=False))

    # Handle button click
    if generate_clicked:
        if config.BACKGROUND_REFRESH:
            # VPS mode: button shows cached, with toast
            if insights_data:
                st.toast(
                    f"Insights refresh every {config.REFRESH_INTERVAL_HOURS} hours",
                    icon="ℹ️"
                )
            else:
                st.toast("No cached insights available", icon="⚠️")
        else:
            # Local mode: button triggers API call
            with st.spinner("Generating insights..."):
                insights_data = asyncio.run(data_service.get_insights(ticker, force_refresh=True))

    # Display insights
    if insights_data:
        insight_text = insights_data.get("insight", "")

        if insights_data.get("is_cached"):
            render_data_age_indicator("Insights", insights_data.get("data_age"))

        # Stream effect for fresh insights, plain text for cached
        # Display in custom styled box for visual emphasis
        if insights_data.get("is_cached"):
            st.markdown(
                f'<div style="background-color: rgba(34, 197, 94, 0.1); '
                f'border-left: 4px solid #22c55e; padding: 1rem; '
                f'border-radius: 0.5rem; color: #fafafa;">{insight_text}</div>',
                unsafe_allow_html=True
            )
        else:
            # Stream into custom styled container
            accumulated_text = ""
            placeholder = st.empty()
            for char in _stream_text(insight_text):
                accumulated_text += char
                placeholder.markdown(
                    f'<div style="background-color: rgba(34, 197, 94, 0.1); '
                    f'border-left: 4px solid #22c55e; padding: 1rem; '
                    f'border-radius: 0.5rem; color: #fafafa;">{accumulated_text}</div>',
                    unsafe_allow_html=True
                )

        # Disclaimer below insights
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.caption("⚠️ This application is for educational and demonstration purposes only. It does not provide financial, investment, legal, or professional advice. Stock data and AI-generated insights should not be used as the basis for any investment decisions. Always consult with qualified financial professionals before making investment decisions. The developers are not responsible for any financial losses or damages resulting from the use of this application.")
    else:
        st.info("Click 'Generate Insights' to get AI analysis.")

def _stream_text(text: str):
    """Generator for streaming text effect."""
    for char in text:
        yield char
        time.sleep(config.STREAMING_CHAR_DELAY)

def render_data_age_indicator(section: str, age: str):
    """Render a small indicator showing data age."""
    if age:
        st.caption(f"⏱️ {section} data from {age}")

def render_related_stocks(related_data: dict):
    """Render related stocks with price and daily change."""
    if not related_data:
        return

    st.markdown("### Related Stocks")

    cols = st.columns(len(related_data))
    for idx, (ticker, data) in enumerate(related_data.items()):
        with cols[idx]:
            current = data.get("current", 0)
            change_pct = data.get("change_pct", 0)

            # Get ticker info for name and exchange
            info = config.TICKER_INFO.get(ticker, {})
            name = info.get("name", ticker)
            exchange = info.get("exchange", "")

            # Larger ticker label
            st.markdown(f"**{ticker}**")
            st.metric(
                label="Price",
                value=f"${current:,.2f}",
                delta=f"{change_pct:+.2f}%",
                label_visibility="collapsed"
            )
            if name and exchange:
                st.caption(f"{name} · {exchange}")
