cat > live_dashboard.py << 'EOF'
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import yfinance as yf
import time
from datetime import datetime

st.set_page_config(page_title="Elite Quant LIVE", layout="wide")
st.title("🚀 Elite Quant LIVE Dashboard")

engine = create_engine("sqlite:///quant_historical.db")

@st.cache_data(ttl=5)
def load_historical():
    return pd.read_sql("SELECT * FROM price_history ORDER BY timestamp DESC LIMIT 20000", engine)

# Live price fetch
def get_live_price(ticker):
    try:
        data = yf.Ticker(ticker).info
        return {
            "price": data.get("regularMarketPrice") or data.get("currentPrice"),
            "change": data.get("regularMarketChangePercent"),
            "volume": data.get("volume")
        }
    except:
        return {"price": None, "change": None, "volume": None}

# UI
col1, col2 = st.columns([3, 1])

with col1:
    tickers = ["AAPL", "TSLA", "NVDA", "SPY"]
    selected = st.selectbox("Select Ticker", tickers)

with col2:
    auto_refresh = st.checkbox("Auto Refresh (5s)", value=True)

# Live metrics
live = get_live_price(selected)
hist_df = load_historical()
ticker_hist = hist_df[hist_df['ticker'] == selected].sort_values("timestamp")

if live["price"]:
    delta = f"{live['change']:+.2f}%" if live["change"] else "N/A"
    st.metric(f"**{selected} LIVE**", f"${live['price']:.2f}", delta)
else:
    st.metric(f"{selected} (Last Close)", f"${ticker_hist['close'].iloc[0]:.2f}" if not ticker_hist.empty else "N/A")

# Chart
fig = px.line(ticker_hist, x="timestamp", y="close", title=f"{selected} Price History + Live")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(ticker_hist.head(10), use_container_width=True)

st.sidebar.info(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if auto_refresh:
    time.sleep(5)
    st.rerun()
EOF