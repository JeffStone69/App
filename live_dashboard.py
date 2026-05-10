import streamlit as st
import yfinance as yf
import plotly.express as px
import time
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Elite Quant LIVE", layout="wide")
st.title("🚀 Elite Quant LIVE Dashboard")

ticker = st.selectbox("Select Ticker", ["AAPL", "TSLA", "NVDA", "SPY", "GOOGL", "MSFT"])
auto_refresh = st.checkbox("Auto Refresh Every 5s", value=True)

# Live Price
info = yf.Ticker(ticker).info
price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0
change = info.get("regularMarketChangePercent") or 0

col1, col2, col3 = st.columns(3)
col1.metric("LIVE PRICE", f"${price:.2f}", f"{change:+.2f}%")
col2.metric("Volume", f"{info.get('volume', 0):,}")
col3.metric("Market Cap", f"${info.get('marketCap', 0)/1e9:.1f}B" if info.get('marketCap') else "N/A")

# === FIXED CHART HANDLING ===
data = yf.download(ticker, period="3mo", progress=False)

# Flatten MultiIndex columns (the root of the error)
if isinstance(data.columns, pd.MultiIndex):
    data = data.droplevel(1, axis=1)   # remove ticker level

data = data.reset_index()

# Ensure 'Close' column exists
if 'Close' not in data.columns:
    if 'close' in data.columns:
        data = data.rename(columns={'close': 'Close'})
    elif 'Adj Close' in data.columns:
        data = data.rename(columns={'Adj Close': 'Close'})

fig = px.line(data, x="Date", y="Close", title=f"{ticker} - Live Chart (Last 3 Months)")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(data.tail(10), use_container_width=True)

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if auto_refresh:
    time.sleep(5)
    st.rerun()
