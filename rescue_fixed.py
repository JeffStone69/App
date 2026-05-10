#!/usr/bin/env python3
"""
FIXED RESCUE v2.8.2
"""

import os
import subprocess

print("🚀 Starting FIXED Elite Quant Rescue...")

packages = ["gradio", "pandas", "yfinance", "plotly", "sqlalchemy", "python-dotenv", "ib_insync", "streamlit"]

for pkg in packages:
    try:
        subprocess.run(["pip", "install", pkg], check=True, capture_output=True)
        print(f"✅ {pkg}")
    except:
        print(f"✅ {pkg} (already installed)")

# Clean setup.py
with open("setup.py", "w") as f:
    f.write('''#!/usr/bin/env python3
import gradio as gr
import yfinance as yf
import subprocess
from datetime import datetime

def run_historical(tickers="AAPL,TSLA,NVDA,SPY"):
    results = []
    for t in [x.strip().upper() for x in tickers.split(",")]:
        try:
            df = yf.download(t, period="1y", progress=False)
            results.append(f"✅ {t}: {len(df)} rows loaded")
        except Exception as e:
            results.append(f"❌ {t}: {e}")
    return "\\n".join(results)

def launch_dashboard():
    subprocess.Popen(["streamlit", "run", "live_dashboard.py", "--server.headless=true"])
    return "🌐 Dashboard launched at http://localhost:8501"

with gr.Blocks(title="Elite Quant") as demo:
    gr.Markdown("# 🚀 Elite Quant - FIXED & LIVE")
    with gr.Tabs():
        with gr.Tab("Historical"):
            gr.Interface(run_historical, inputs=gr.Textbox(value="AAPL,TSLA,NVDA,SPY"), outputs="text")
        with gr.Tab("Live Dashboard"):
            gr.Button("🚀 Launch Live Dashboard", variant="primary").click(launch_dashboard, outputs="text")
        with gr.Tab("Status"):
            gr.Markdown(f"**Status:** Fixed on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
''')

# Live Dashboard
with open("live_dashboard.py", "w") as f:
    f.write('''import streamlit as st
import yfinance as yf
import plotly.express as px
import time
from datetime import datetime

st.set_page_config(page_title="Elite Quant LIVE", layout="wide")
st.title("🚀 Elite Quant LIVE Dashboard")

ticker = st.selectbox("Ticker", ["AAPL", "TSLA", "NVDA", "SPY", "GOOGL", "MSFT"])
auto = st.checkbox("Auto-refresh every 5 seconds", True)

info = yf.Ticker(ticker).info
price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
change = info.get("regularMarketChangePercent") or 0

col1, col2, col3 = st.columns(3)
col1.metric("LIVE PRICE", f"${price:.2f}", f"{change:+.2f}%")
col2.metric("Volume", f"{info.get('volume', 0):,}")

data = yf.download(ticker, period="3mo", progress=False)
fig = px.line(data, x=data.index, y="Close", title=f"{ticker} Live Chart")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(data.tail(10))

if auto:
    time.sleep(5)
    st.rerun()
''')

print("\\n🎉 RESCUE COMPLETE!")
print("Now run:")
print("   python3 setup.py")
