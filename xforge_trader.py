#!/usr/bin/env python3
"""
XForge Trader v10.1 – Full Standalone Production App
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
from contextlib import contextmanager

import gradio as gr
import pandas as pd
import yfinance as yf
import sqlite3

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "xforge_historical.db"

def setup_logging():
    logger = logging.getLogger("XForge")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    fileh = logging.FileHandler("xforge_errors.log", mode="a")
    fileh.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(fileh)
    return logger

logger = setup_logging()

@contextmanager
def db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        yield conn
    finally:
        conn.close()

# ====================== TAB BUILDERS (Full from original) ======================

def build_watchlist_tab():
    with gr.Column():
        gr.Markdown("## Real-Time Multi-Ticker Watchlist")
        tickers_input = gr.Textbox(label="Tickers (comma-separated)", value="TSLA,AAPL,GOOGL,MSFT,NVDA")
        watchlist_table = gr.DataFrame(label="Live Watchlist")
        status = gr.Markdown("Ready")

        def update_watchlist(tickers_str):
            try:
                tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
                data = []
                for t in tickers[:10]:
                    info = yf.Ticker(t).fast_info
                    price = round(info.get('lastPrice') or info.get('regularMarketPrice', 0), 2)
                    change_pct = round((info.get('regularMarketChangePercent') or 0) * 100, 2)
                    volume = int(info.get('regularMarketVolume', 0))
                    signal = "BUY" if change_pct > 0.5 else "SELL" if change_pct < -0.5 else "HOLD"
                    data.append({"Ticker": t, "Price": price, "% Change": change_pct, "Volume": volume, "Signal": signal, "Last Updated": datetime.now().strftime("%H:%M:%S")})
                return pd.DataFrame(data)
            except Exception as e:
                logger.error(f"Watchlist error: {e}")
                return pd.DataFrame([{"Error": str(e)}])

        gr.Button("Refresh").click(update_watchlist, inputs=tickers_input, outputs=watchlist_table)

def build_strategy_optimizer_tab():
    with gr.Column():
        gr.Markdown("## Strategy Optimizer")
        ticker_opt = gr.Textbox(label="Ticker", value="TSLA")
        optimize_btn = gr.Button("Run Optimization")
        result_md = gr.Markdown()

        def optimize(ticker):
            try:
                df = yf.download(ticker, period="1y", progress=False)
                df['SMA20'] = df['Close'].rolling(20).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                buys = (df['SMA20'] > df['SMA50']) & (df['SMA20'].shift(1) <= df['SMA50'].shift(1))
                returns = df['Close'].pct_change()[buys].sum() * 100
                return f"**Optimized Return for {ticker}: {returns:.2f}%**"
            except Exception as e:
                logger.error(f"Optimizer error: {e}")
                return f"Error: {str(e)}"
        optimize_btn.click(optimize, inputs=ticker_opt, outputs=result_md)

def build_historical_database_tab():
    with gr.Column():
        gr.Markdown("## Historical Database Builder")
        tickers_input = gr.Textbox(label="Tickers", value="TSLA")
        fetch_btn = gr.Button("Fetch & Store")
        preview = gr.DataFrame()
        status = gr.Markdown("Ready")

        def fetch_and_store(tickers_str):
            try:
                tickers = [t.strip().upper() for t in tickers_str.split(",")]
                df = yf.download(tickers[0], period="1y", progress=False)
                df = df.reset_index()
                df['ticker'] = tickers[0]
                with db_connection() as conn:
                    df.to_sql('historical_prices', conn, if_exists='append', index=False)
                return df.head(10), "✅ Data stored successfully"
            except Exception as e:
                logger.error(f"DB error: {e}")
                return pd.DataFrame(), f"Error: {str(e)}"
        fetch_btn.click(fetch_and_store, inputs=tickers_input, outputs=[preview, status])

def create_xforge_app():
    try:
        css = """
        .gradio-container { background: linear-gradient(135deg, #0a0f1a 0%, #1f2937 100%); color: #e2e8f0; }
        """
        with gr.Blocks(title="XForge Trader v10.1", theme=gr.themes.Default(), css=css) as demo:
            gr.Markdown("# XFORGE TRADER v10.1\n**Standalone • Robust • Always Launches**")
            with gr.Tabs():
                with gr.Tab("Watchlist"): build_watchlist_tab()
                with gr.Tab("Strategy Optimizer"): build_strategy_optimizer_tab()
                with gr.Tab("Historical Database"): build_historical_database_tab()
            gr.Markdown("**Logs:** XForge_Beta.log | xforge_errors.log")
            return demo
    except Exception as e:
        logger.error(f"App creation failed: {e}")
        with gr.Blocks() as demo:
            gr.Markdown("# XForge Trader\n**Fallback mode active** — Check logs.")
            return demo

if __name__ == "__main__":
    logger.info("=== XForge Trader v10.1 Starting ===")
    try:
        app = create_xforge_app()
        app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            inbrowser=True,
            show_api=False,
            share=False,
            quiet=True
        )
    except Exception as e:
        logger.error(f"Critical launch failure: {e}")
        print("❌ Launch failed. Full details in xforge_errors.log")
