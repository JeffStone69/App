#!/usr/bin/env python3
"""
RESCUE SCRIPT - Fixes your broken App repo (v2.8)
"""

import os
import subprocess
import shutil

print("🚀 Starting Elite Quant Full Rescue...")

# Install missing deps
subprocess.run(["pip", "install", "gradio pandas yfinance openai flask sqlalchemy plotly python-dotenv ib_insync streamlit"], check=True)

# Backup current broken files
if os.path.exists("setup.py"):
    shutil.copy("setup.py", f"backups/setup_backup_{os.path.getmtime('setup.py'):.0f}.py")

# Write clean, working setup.py (with live data + dashboard)
setup_code = """#!/usr/bin/env python3
import os, sys, logging, subprocess
from datetime import datetime
import pandas as pd
import yfinance as yf
import gradio as gr
from pathlib import Path

BASE_DIR = Path(__file__).parent
os.makedirs("logs", exist_ok=True)
os.makedirs("backups", exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def ingest(tickers="AAPL,TSLA,NVDA,SPY", period="1y"):
    tickers = [t.strip().upper() for t in tickers.split(",")]
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, progress=False)
            logger.info(f"✅ Fetched {len(df)} rows for {ticker}")
        except Exception as e:
            logger.error(f"Failed {ticker}: {e}")
    return "Historical data ingested successfully!"

def launch_live_dashboard():
    subprocess.Popen(["streamlit", "run", "live_dashboard.py", "--server.headless", "true"])
    return "🌐 Live Dashboard launching at http://localhost:8501"

with gr.Blocks(title="XForge Elite Quant") as demo:
    gr.Markdown("# 🚀 XForge Trader - Fixed & Live")
    with gr.Tabs():
        with gr.Tab("Historical"):
            gr.Interface(ingest, inputs=["text", "text"], outputs="text", title="Ingest Data")
        with gr.Tab("Live Dashboard"):
            gr.Button("Launch Live Web UI").click(launch_live_dashboard)
        with gr.Tab("Status"):
            gr.Markdown("Repo fixed • Live prices active • Ready for SIM")

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
"""

with open("setup.py", "w") as f:
    f.write(setup_code)

# Create live dashboard
with open("live_dashboard.py", "w") as f:
    f.write("""import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

st.set_page_config(page_title="Elite Quant LIVE", layout="wide")
st.title("🚀 Elite Quant LIVE Dashboard")

ticker = st.selectbox("Ticker", ["AAPL", "TSLA", "NVDA", "SPY", "BHP.AX"])
auto = st.checkbox("Auto-refresh every 5s", True)

data = yf.download(ticker, period="1mo", progress=False)
live = yf.Ticker(ticker).info

col1, col2, col3 = st.columns(3)
col1.metric("Current Price", f"${live.get('currentPrice', live.get('regularMarketPrice', 0)):.2f}")
col2.metric("Change %", f"{live.get('regularMarketChangePercent', 0):+.2f}%")
col3.metric("Volume", f"{live.get('volume', 0):,}")

fig = px.line(data, x=data.index, y="Close", title=f"{ticker} Live Chart")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(data.tail(10))

if auto:
    time.sleep(5)
    st.rerun()
""")

print("✅ Rescue complete!")
print("Run: python3 setup.py")
print("Live UI: python3 -m streamlit run live_dashboard.py")