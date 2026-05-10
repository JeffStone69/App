import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from sqlalchemy import create_engine
import time
from datetime import datetime

st.set_page_config(page_title="Elite Quant LIVE", layout="wide")
st.title("🚀 Elite Quant LIVE + IBKR Feed")

engine = create_engine("sqlite:///quant_historical.db")

ticker = st.selectbox("Ticker", ["AAPL", "TSLA", "NVDA", "SPY"])
auto = st.checkbox("Auto-refresh (5s)", True)

# Live price (fallback + IBKR data)
info = yf.Ticker(ticker).info
price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

# Pull latest from DB (IBKR bars)
df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY timestamp DESC LIMIT 100", engine)

col1, col2, col3 = st.columns(3)
col1.metric("LIVE PRICE", f"${price:.2f}")
col2.metric("Latest DB Bar", f"${df['close'].iloc[0]:.2f}" if not df.empty else "N/A")
col3.metric("Bars in DB", len(df))

fig = px.line(df.sort_values("timestamp"), x="timestamp", y="close", title=f"{ticker} — IBKR Live Bars")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df.head(10), use_container_width=True)

if auto:
    time.sleep(5)
    st.rerun()
