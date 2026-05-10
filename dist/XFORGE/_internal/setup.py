#!/usr/bin/env python3
"""
Elite Quant v3.0 — IBKR Live + Backtester + Rollback
"""

import os
import sys
import subprocess
import asyncio
import pandas as pd
import yfinance as yf
import gradio as gr
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from sqlalchemy import create_engine, text

# ========================= CONFIG =========================
os.makedirs("logs", exist_ok=True)
os.makedirs("backups", exist_ok=True)
DB_URL = "sqlite:///quant_historical.db"
engine = create_engine(DB_URL, echo=False)

try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

# ========================= ROLLBACK SAFETY =========================
def backup_db():
    db_file = "quant_historical.db"
    if os.path.exists(db_file):
        shutil.copy(db_file, f"backups/quant_historical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        print("✅ DB backed up")

def rollback_db():
    backups = sorted(Path("backups").glob("quant_historical_*.db"), reverse=True)
    if backups:
        latest = backups[0]
        shutil.copy(latest, "quant_historical.db")
        print(f"✅ Rolled back to {latest.name}")
    else:
        print("❌ No backup found")

# ========================= IBKR LIVE FEED =========================
ib = None

async def start_ibkr_live(tickers):
    global ib
    if not IB_AVAILABLE:
        return "❌ ib_insync not installed"
    backup_db()
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=999)
        print("✅ Connected to IBKR")
        
        contracts = [Stock(t, 'SMART', 'USD') for t in tickers]
        contracts = ib.qualifyContracts(*contracts)
        
        for c in contracts:
            ib.reqRealTimeBars(c, 5, "TRADES", False)
            print(f"📡 Subscribed to real-time bars: {c.symbol}")
        
        @ib.realTimeBarsEvent
        def on_bar(bar):
            df = util.df([bar])
            df['ticker'] = bar.contract.symbol
            df = df[['ticker', 'time', 'open', 'high', 'low', 'close', 'volume']]
            df.rename(columns={'time': 'timestamp'}, inplace=True)
            df.to_sql('price_history', engine, if_exists='append', index=False, method='multi')
            print(f"LIVE BAR → {bar.contract.symbol} | Close: {bar.close}")
        
        await asyncio.sleep(3600)  # keep alive
    except Exception as e:
        print(f"IBKR error: {e}")
        rollback_db()
        return f"❌ Live feed failed → rollback triggered"

# ========================= BACKTESTER =========================
def run_backtest(ticker="AAPL", strategy="SMA_Crossover", period="2y"):
    backup_db()
    try:
        data = yf.download(ticker, period=period, progress=False)
        data['SMA50'] = data['Close'].rolling(50).mean()
        data['SMA200'] = data['Close'].rolling(200).mean()
        
        data['Signal'] = 0
        data['Signal'] = data['SMA50'] > data['SMA200']
        data['Position'] = data['Signal'].diff()
        
        data['Returns'] = data['Close'].pct_change()
        data['Strategy'] = data['Returns'] * data['Signal'].shift(1)
        
        total_return = data['Strategy'].sum()
        sharpe = data['Strategy'].mean() / data['Strategy'].std() * (252**0.5) if data['Strategy'].std() != 0 else 0
        
        result = f"""
        ✅ Backtest Complete
        Ticker: {ticker}
        Strategy: {strategy}
        Total Return: {total_return*100:.2f}%
        Sharpe Ratio: {sharpe:.2f}
        Max Drawdown: {(data['Strategy'].cumsum().min())*100:.2f}%
        """
        return result
    except Exception as e:
        rollback_db()
        return f"❌ Backtest failed → rollback triggered\n{e}"

# ========================= GRADIO UI =========================
def launch_live():
    tickers = ["AAPL", "TSLA", "NVDA", "SPY"]
    asyncio.run(start_ibkr_live(tickers))
    return "✅ IBKR Live Feed Started (check terminal + dashboard)"

with gr.Blocks(title="Elite Quant v3.0") as demo:
    gr.Markdown("# 🚀 Elite Quant v3.0 — IBKR Live + Backtester + Rollback")
    with gr.Tabs():
        with gr.Tab("📡 IBKR Live Feed"):
            gr.Button("Start Full IBKR Live Feed", variant="primary").click(launch_live, outputs=gr.Textbox())
        with gr.Tab("📊 Backtester"):
            gr.Interface(
                fn=run_backtest,
                inputs=[
                    gr.Textbox(value="AAPL", label="Ticker"),
                    gr.Dropdown(["SMA_Crossover"], value="SMA_Crossover", label="Strategy")
                ],
                outputs=gr.Textbox(label="Backtest Results")
            )
        with gr.Tab("🔄 Rollback"):
            gr.Button("Manual Rollback (Last Backup)", variant="stop").click(lambda: rollback_db(), outputs=gr.Textbox())
        with gr.Tab("Live Dashboard"):
            gr.Markdown("Open separately: `python3 -m streamlit run live_dashboard.py`")

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
