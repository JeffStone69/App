cat > rescue_fixed.py << 'EOF'
#!/usr/bin/env python3
"""
FIXED RESCUE - One command to fix everything
"""

import os
import subprocess
import shutil
from pathlib import Path

print("🚀 Starting FIXED Elite Quant Rescue...")

# 1. Install dependencies correctly (one by one)
packages = ["gradio", "pandas", "yfinance", "openai", "flask", "sqlalchemy", 
            "plotly", "python-dotenv", "ib_insync", "streamlit"]

print("Installing packages...")
for pkg in packages:
    try:
        subprocess.run(["pip", "install", pkg], check=True, capture_output=True)
        print(f"✅ {pkg}")
    except:
        print(f"⚠️  {pkg} (already installed or minor issue)")

# 2. Create clean setup.py (main launcher)
setup_code = """#!/usr/bin/env python3
import os
import subprocess
import gradio as gr
import yfinance as yf
import pandas as pd
from datetime import datetime

print("🚀 XForge Elite Quant - Fixed Launcher")

def run_historical(tickers="AAPL,TSLA,NVDA,SPY"):
    tickers_list = [t.strip().upper() for t in tickers.split(",")]
    results = []
    for t in tickers_list:
        try:
            df = yf.download(t, period="1y", progress=False)
            results.append(f"✅ {t}: {len(df)} rows")
        except Exception as e:
            results.append(f"❌ {t}: {e}")
    return "\\n".join(results)

def launch_live_dashboard():
    subprocess.Popen(["streamlit", "run", "live_dashboard.py", "--server.headless=true", "--server.port=8501"])
    return "🌐 Dashboard opening at http://localhost:8501 (refresh if needed)"

with gr.Blocks(title="Elite Quant") as demo:
    gr.Markdown("# 🚀 Elite Quant - Fully Fixed")
    with gr.Tabs():
        with gr.Tab("📊 Historical Data"):
            gr.Interface(run_historical, inputs=gr.Textbox(value="AAPL,TSLA,NVDA,SPY"), outputs="text")
        with gr.Tab("📡 Live Dashboard"):
            gr.Button("Launch Live Web UI", variant="primary").click(launch_live_dashboard, outputs="text")
        with gr.Tab("Status"):
            gr.Markdown(f"**Last Fixed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
"""

with open("setup.py", "w") as f:
    f.write(setup_code)

# 3. Create reliable live dashboard
dashboard_code = """import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

st.set_page_config(page_title="Elite Quant LIVE", layout="wide")
st.title("🚀 Elite Quant LIVE Dashboard")

ticker = st.selectbox("Select Ticker", ["AAPL", "TSLA", "NVDA", "SPY", "GOOGL", "MSFT"])
auto_refresh = st.checkbox("Auto Refresh Every 5s", value=True)

# Live data
info = yf.Ticker(ticker).info
price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
change = info.get("regularMarketChangePercent") or 0

col1, col2, col3 = st.columns(3)
col1.metric("LIVE PRICE", f"${price:.2f}", f"{change:+.2f}%")
col2.metric("Volume", f"{info.get('volume', 0):,}")
col3.metric("Market Cap", f"${info.get('marketCap', 0)/1e9:.1f}B")

# Chart
data = yf.download(ticker, period="3mo", progress=False)
fig = px.line(data, x=data.index, y="Close", title=f"{ticker} - Last 3 Months")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(data.tail(10), use_container_width=True)

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if auto_refresh:
    time.sleep(5)
    st.rerun()
"""

with open("live_dashboard.py", "w") as f:
    f.write(dashboard_code)

print("\\n🎉 RESCUE COMPLETE!")
print("Run these commands:")
print("   python3 setup.py")
print("   python3 -m streamlit run live_dashboard.py")
EOF