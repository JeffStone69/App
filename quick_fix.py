#!/usr/bin/env python3
"""
QUICK FIX: Inject Web UI + Streamlit Dashboard
Run this once → adds full web dashboard
"""

import os
import subprocess
import shutil
from datetime import datetime

print("🚀 Elite Quant Quick Fix - Injecting Web Dashboard...")

# Ensure Streamlit is installed
print("Installing Streamlit...")
subprocess.run(["pip", "install", "streamlit"], check=True)

# Create dashboard.py
dashboard_code = """import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(page_title="Elite Quant", layout="wide")
st.title("🚀 Elite Quant Live Dashboard")

engine = create_engine("sqlite:///quant_historical.db")

@st.cache_data(ttl=30)
def load_data():
    return pd.read_sql("SELECT * FROM price_history ORDER BY timestamp DESC LIMIT 10000", engine)

df = load_data()

if df.empty:
    st.warning("No data yet. Run historical build first.")
else:
    ticker = st.selectbox("Ticker", sorted(df['ticker'].unique()))
    tdf = df[df['ticker'] == ticker].sort_values("timestamp")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Price", f"${tdf['close'].iloc[0]:.2f}")
    col2.metric("Volume", f"{int(tdf['volume'].iloc[0]):,}")
    col3.metric("Records", len(tdf))
    
    fig = px.line(tdf, x="timestamp", y="close", title=f"{ticker} Price History")
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(tdf.head(20), use_container_width=True)

st.sidebar.info("💡 Run: python3 setup.py --force to refresh data")
"""

with open("dashboard.py", "w") as f:
    f.write(dashboard_code)

print("✅ dashboard.py created")

# Patch setup.py to support --dashboard
with open("setup.py", "r") as f:
    content = f.read()

if "--dashboard" not in content:
    # Simple append at the end (before if __name__)
    patch = """
# QUICK FIX PATCH - Web Dashboard
def launch_dashboard():
    print("\\n🌐 Launching Elite Quant Web UI → http://localhost:8501")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py"])

if "--dashboard" in sys.argv or "--all" in sys.argv:
    launch_dashboard()
"""
    # Insert before the final if __name__ block
    if "if __name__" in content:
        content = content.replace("if __name__ == \"__main__\":", patch + "\nif __name__ == \"__main__\":")
    else:
        content += patch + "\nif __name__ == \"__main__\":\n    main()"

    with open("setup.py", "w") as f:
        f.write(content)

print("✅ setup.py patched with dashboard support")

# Final launch
print("\\n🎉 Quick Fix Complete!")
print("Launching dashboard now...")
os.system("python3 -m streamlit run dashboard.py --server.headless true")