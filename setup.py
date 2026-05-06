#!/usr/bin/env python3
"""
XForge Trader - Historical Stock Database v1.0
Production-optimized single-file setup & app
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path.cwd()
VENV_DIR = BASE_DIR / "venv"
APP_FILE = BASE_DIR / "xforge_historical_db.py"
LOG_FILE = BASE_DIR / "xforge_errors.log"
DB_FILE = BASE_DIR / "stock_history.db"

# Robust logging setup
logger = logging.getLogger("XForgeHistorical")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, mode="a")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler(sys.stdout))

def create_full_app():
    app_code = '''#!/usr/bin/env python3
"""
XForge Trader - Historical Stock Database v1.0
Complete production-grade single-file app
"""

import sys
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import gradio as gr
import pandas as pd
import yfinance as yf

# === CONFIG ===
BASE_DIR = Path.cwd()
DB_PATH = BASE_DIR / "stock_history.db"
LOG_PATH = BASE_DIR / "xforge_errors.log"

# Robust error logging
logger = logging.getLogger("XForgeDB")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_PATH, mode="a")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler(sys.stdout))

# === DATABASE LAYER (robust fetch handling) ===
def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        raise

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                market TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, date)
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        raise

def save_to_db(df, ticker, market):
    if df.empty:
        return 0
    try:
        conn = get_db_connection()
        df = df.reset_index()
        df["ticker"] = ticker
        df["market"] = market
        df["fetched_at"] = datetime.now().isoformat()
        df = df.rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume"
        })
        df.to_sql("stock_history", conn, if_exists="append", index=False,
                  method="multi", chunksize=500)
        conn.commit()
        rows = len(df)
        conn.close()
        logger.info(f"Saved {rows} rows for {ticker}")
        return rows
    except Exception as e:
        logger.error(f"DB save failed for {ticker}: {e}")
        return 0

def fetch_historical_data(ticker, start, end, market):
    try:
        ticker = ticker.strip().upper()
        if not ticker:
            raise ValueError("Ticker cannot be empty")
        
        # yfinance with cache management & resilience
        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(start=start, end=end, auto_adjust=True, 
                               progress=False, timeout=30)
        
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return pd.DataFrame(), 0
        
        rows = save_to_db(df, ticker, market)
        return df.tail(10), rows  # Return preview + count
    except Exception as e:
        logger.error(f"Fetch error for {ticker}: {str(e)}")
        return pd.DataFrame([{"Error": str(e)}]), 0

def query_database(ticker_filter, start_date, end_date):
    try:
        conn = get_db_connection()
        query = """
            SELECT ticker, date, open, high, low, close, volume, market, fetched_at
            FROM stock_history
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        
        if ticker_filter and ticker_filter.strip():
            query += " AND ticker = ?"
            params.append(ticker_filter.strip().upper())
        
        query += " ORDER BY date DESC LIMIT 500"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return pd.DataFrame([{"Error": str(e)}])

def get_available_tickers():
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT DISTINCT ticker FROM stock_history ORDER BY ticker", conn)
        conn.close()
        return ["All"] + df["ticker"].tolist()
    except:
        return ["All"]

# === GRADIO UI (combined tabs, user-friendly) ===
def build_fetch_tab():
    with gr.Column():
        gr.Markdown("## 📥 Fetch & Store Historical Data")
        
        with gr.Row():
            market = gr.Dropdown(
                choices=["US", "Europe", "Asia", "Global"],
                value="US",
                label="Market"
            )
            ticker_input = gr.Textbox(
                value="AAPL,MSFT,GOOGL",
                label="Tickers (comma-separated)",
                placeholder="TSLA,AAPL,NVDA"
            )
        
        with gr.Row():
            period = gr.Radio(
                choices=["1 Month", "3 Months", "6 Months", "1 Year", "5 Years", "Max", "Custom"],
                value="1 Year",
                label="Time Period"
            )
            custom_start = gr.Textbox(label="Start Date (YYYY-MM-DD)", visible=False)
            custom_end = gr.Textbox(label="End Date (YYYY-MM-DD)", visible=False)
        
        fetch_btn = gr.Button("Fetch & Store to Database", variant="primary", size="lg")
        
        with gr.Row():
            preview = gr.DataFrame(label="Preview (last 10 rows)")
            status = gr.Markdown("Status: Ready")
        
        def on_period_change(period_val):
            if period_val == "Custom":
                return gr.update(visible=True), gr.update(visible=True)
            return gr.update(visible=False), gr.update(visible=False)
        
        period.change(on_period_change, inputs=period, outputs=[custom_start, custom_end])
        
        def fetch_action(market, tickers_str, period, start_custom, end_custom):
            try:
                tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
                if not tickers:
                    return pd.DataFrame(), "❌ No tickers provided"
                
                # Calculate dates
                today = datetime.now()
                if period == "1 Month":
                    start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
                    end = today.strftime("%Y-%m-%d")
                elif period == "3 Months":
                    start = (today - timedelta(days=90)).strftime("%Y-%m-%d")
                    end = today.strftime("%Y-%m-%d")
                elif period == "6 Months":
                    start = (today - timedelta(days=180)).strftime("%Y-%m-%d")
                    end = today.strftime("%Y-%m-%d")
                elif period == "1 Year":
                    start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
                    end = today.strftime("%Y-%m-%d")
                elif period == "5 Years":
                    start = (today - timedelta(days=1825)).strftime("%Y-%m-%d")
                    end = today.strftime("%Y-%m-%d")
                elif period == "Max":
                    start = "1900-01-01"
                    end = today.strftime("%Y-%m-%d")
                else:
                    start = start_custom or (today - timedelta(days=365)).strftime("%Y-%m-%d")
                    end = end_custom or today.strftime("%Y-%m-%d")
                
                total_rows = 0
                all_previews = []
                
                for t in tickers[:10]:  # Limit to 10 tickers per batch
                    df_preview, rows = fetch_historical_data(t, start, end, market)
                    total_rows += rows
                    if not df_preview.empty and "Error" not in df_preview.columns:
                        all_previews.append(df_preview)
                
                combined_preview = pd.concat(all_previews) if all_previews else pd.DataFrame()
                status_msg = f"✅ Successfully stored {total_rows} rows across {len(tickers)} tickers"
                
                return combined_preview, status_msg
            except Exception as e:
                logger.error(f"Fetch action error: {e}")
                return pd.DataFrame([{"Error": str(e)}]), f"❌ Error: {str(e)}"
        
        fetch_btn.click(
            fetch_action,
            inputs=[market, ticker_input, period, custom_start, custom_end],
            outputs=[preview, status]
        )

def build_view_tab():
    with gr.Column():
        gr.Markdown("## 📊 View Historical Database")
        
        with gr.Row():
            ticker_select = gr.Dropdown(
                choices=get_available_tickers(),
                value="All",
                label="Filter by Ticker"
            )
            start_date = gr.Textbox(value=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"), label="Start Date")
            end_date = gr.Textbox(value=datetime.now().strftime("%Y-%m-%d"), label="End Date")
        
        query_btn = gr.Button("Query Database", variant="secondary")
        results = gr.DataFrame(label="Historical Data (latest 500 rows)")
        
        def query_action(ticker, start, end):
            if ticker == "All":
                ticker = ""
            return query_database(ticker, start, end)
        
        query_btn.click(query_action, inputs=[ticker_select, start_date, end_date], outputs=results)

def build_logs_tab():
    with gr.Column():
        gr.Markdown("## 📋 Error Logs & System Status")
        log_output = gr.Textbox(label="Recent Errors (last 50 lines)", lines=15, interactive=False)
        refresh_btn = gr.Button("Refresh Logs")
        
        def read_logs():
            try:
                with open(LOG_PATH, "r") as f:
                    lines = f.readlines()[-50:]
                    return "".join(lines)
            except:
                return "No logs yet"
        
        refresh_btn.click(read_logs, outputs=log_output)

def create_app():
    init_db()
    
    with gr.Blocks(
        title="XForge Historical Stock DB v1.0",
        theme=gr.themes.Soft(),
        css=".gradio-container {max-width: 1200px; margin: auto;}"
    ) as demo:
        gr.Markdown("# XFORGE HISTORICAL STOCK DATABASE v1.0")
        gr.Markdown("Production-ready • SQLite-backed • yfinance-powered • Auto-cached")
        
        with gr.Tabs():
            with gr.Tab("Fetch Data"):
                build_fetch_tab()
            with gr.Tab("View Database"):
                build_view_tab()
            with gr.Tab("Logs & Status"):
                build_logs_tab()
        
        gr.Markdown("**Database:** stock_history.db | **Logs:** xforge_errors.log | **Cache:** Managed by yfinance")
    
    return demo

if __name__ == "__main__":
    logger.info("=== XForge Historical DB v1.0 STARTING ===")
    app = create_app()
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, quiet=False)
'''

    APP_FILE.write_text(app_code)
    logger.info(f"Full app written to {APP_FILE}")

# === MAIN SETUP ===
if __name__ == "__main__":
    print("XForge Historical Stock DB v1.0 - Production Setup Starting...")
    
    # Create venv
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    
    # Activate script
    if sys.platform == "win32":
        activate = str(VENV_DIR / "Scripts" / "activate.bat")
        pip_cmd = f'"{activate}" && pip install --upgrade pip gradio yfinance pandas'
        python_cmd = f'"{activate}" && python "{APP_FILE}"'
    else:
        activate = str(VENV_DIR / "bin" / "activate")
        pip_cmd = f'source {activate} && pip install --upgrade pip gradio yfinance pandas'
        python_cmd = f'source {activate} && python "{APP_FILE}"'
    
    print("Installing dependencies...")
    subprocess.run(pip_cmd, shell=True, executable="/bin/bash" if not sys.platform == "win32" else None)
    
    print("Creating full application...")
    create_full_app()
    
    print("Launching XForge Historical Stock Database...")
    subprocess.run(python_cmd, shell=True, executable="/bin/bash" if not sys.platform == "win32" else None)
    
    print("Setup complete. App running at http://127.0.0.1:7860")
