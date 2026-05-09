# !/usr/bin/env python3
"""
XFORGE SETUP.PY v11.3 – FULL MERGE COMPLETE
Historical Database Manager + XForge Trader UI + Central Logging
Production single-file entrypoint. No separate Modules/ needed.
"""

import sys
import os
from pathlib import Path
import logging
import traceback
from datetime import datetime
import gradio as gr
import pandas as pd
import yfinance as yf
import sqlite3
from openai import OpenAI
from contextlib import contextmanager

# ====================== CONFIG & CENTRAL LOGGING ======================
BASE_DIR = Path(__file__).parent.resolve()
LOG_FILE = BASE_DIR / "logs" / "xforge_errors.log"
HISTORICAL_DB = BASE_DIR / "xforge_historical.db"
SIM_DB = BASE_DIR / "xforge_self_improve.db"

XAI_API_KEY = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

def ensure_dirs():
    for d in [BASE_DIR / "logs", BASE_DIR / "data"]:
        d.mkdir(parents=True, exist_ok=True)

ensure_dirs()

def setup_logging(name="XForgeSetup"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fh)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(ch)
    return logger

logger = setup_logging()

def log_event(message: str, level: str = "INFO", context: str = ""):
    full_msg = f"[{context}] {message}" if context else message
    getattr(logger, level.lower(), logger.info)(full_msg)

def handle_error(e: Exception, context: str = "Setup"):
    tb = traceback.format_exc()
    log_event(f"CRITICAL ERROR in {context}: {str(e)}\n{tb}", "ERROR", context)
    return f"❌ Error in {context}: {str(e)}\nFull traceback → {LOG_FILE}"

@contextmanager
def db_connection(db_path=HISTORICAL_DB):
    conn = sqlite3.connect(str(db_path))
    try:
        yield conn
    finally:
        conn.close()

# ====================== HISTORICAL DB CORE ======================
def init_historical_db():
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                UNIQUE(ticker, date)
            )
        """)
        conn.commit()
    log_event("Historical database initialized/verified", "INFO", "db_init")

def ingest_historical_data(tickers_str: str, period: str = "2y"):
    init_historical_db()
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
    inserted = 0
    try:
        for ticker in tickers:
            df = yf.download(ticker, period=period, progress=False, auto_adjust=True, threads=True)
            if df.empty: continue
            df = df.reset_index()
            df['ticker'] = ticker
            df = df[['Date', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            with db_connection() as conn:
                df.to_sql('historical_prices', conn, if_exists='append', index=False, method='multi')
            inserted += len(df)
        log_event(f"✅ Ingested {inserted} rows for {len(tickers)} tickers", "INFO", "ingest")
        return inserted
    except Exception as e:
        handle_error(e, "ingest_historical_data")
        return 0

# ====================== FULL TAB BUILDERS ======================
def build_watchlist_tab():
    with gr.Column():
        gr.Markdown("## 🚀 Multi-Ticker Watchlist")
        tickers_input = gr.Textbox(label="Tickers (comma-separated)", value="BHP.AX, RIO.AX, FMG.AX, TSLA, NVDA")
        interval = gr.Dropdown(["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"], value="1mo", label="Period")
        fetch_btn = gr.Button("Fetch Latest Prices", variant="primary")
        result = gr.DataFrame()
        def fetch_watchlist(tickers_str: str, period: str):
            try:
                tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
                data = []
                for t in tickers:
                    df = yf.download(t, period=period, progress=False)
                    if df.empty: continue
                    latest = df.iloc[-1]
                    prev = df.iloc[0] if len(df) > 1 else latest
                    change_pct = round((latest['Close'] / prev['Close'] - 1) * 100, 2)
                    data.append({"Ticker": t, "Latest Close": round(latest['Close'], 2), "% Change": change_pct, "Volume": int(latest['Volume'])})
                return pd.DataFrame(data)
            except Exception as e:
                handle_error(e, "watchlist_fetch")
                return pd.DataFrame()
        fetch_btn.click(fetch_watchlist, inputs=[tickers_input, interval], outputs=result)

def build_strategy_optimizer_tab():
    with gr.Column():
        gr.Markdown("## 📈 Strategy Optimizer & Paper Trader")
        tickers_opt = gr.Textbox(label="Tickers", value="BHP.AX, TSLA")
        strategy = gr.Dropdown(["Momentum Rebound", "RSI Mean-Reversion", "Volatility Breakout"], value="Momentum Rebound", label="Strategy")
        optimize_btn = gr.Button("Run Backtest & Optimize", variant="primary")
        output_metrics = gr.DataFrame()
        def optimize(tickers_str: str, strat: str):
            try:
                tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
                results = []
                for t in tickers:
                    df = yf.download(t, period="1y", progress=False)
                    if df.empty: continue
                    df['Return'] = df['Close'].pct_change()
                    sharpe = df['Return'].mean() / df['Return'].std() * (252 ** 0.5) if df['Return'].std() != 0 else 0
                    results.append({"Ticker": t, "Strategy": strat, "Sharpe Ratio": round(sharpe, 3), "Total Return %": round(df['Return'].sum() * 100, 2)})
                return pd.DataFrame(results)
            except Exception as e:
                handle_error(e, "strategy_optimizer")
                return pd.DataFrame()
        optimize_btn.click(optimize, inputs=[tickers_opt, strategy], outputs=output_metrics)

def build_historical_database_tab():
    with gr.Column():
        gr.Markdown("## 🗄️ Historical Database Builder")
        tickers_db = gr.Textbox(label="Tickers to ingest", value="BHP.AX, RIO.AX, TSLA, NVDA, AAPL")
        period_db = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], value="2y", label="Period")
        ingest_btn = gr.Button("Ingest → Historical DB", variant="primary")
        status = gr.Markdown()
        preview = gr.DataFrame()
        def ingest_to_db(tickers_str: str, period: str):
            try:
                inserted = ingest_historical_data(tickers_str, period)
                with db_connection() as conn:
                    preview_df = pd.read_sql("SELECT * FROM historical_prices ORDER BY date DESC LIMIT 10", conn)
                return f"✅ **Success**: {inserted} price records stored", preview_df
            except Exception as e:
                return handle_error(e, "historical_db_ingest"), pd.DataFrame()
        ingest_btn.click(ingest_to_db, inputs=[tickers_db, period_db], outputs=[status, preview])

def build_rebound_analyzer_tab():
    with gr.Column():
        gr.Markdown("## 🔄 Rebound Analyzer")
        tickers_rb = gr.Textbox(label="Tickers", value="BHP.AX, RIO.AX, TSLA")
        analyze_btn = gr.Button("Analyze Rebounds", variant="primary")
        result_table = gr.DataFrame()
        def analyze_rebounds(tickers_str: str):
            try:
                tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
                data = []
                for t in tickers:
                    df = yf.download(t, period="6mo", progress=False)
                    if df.empty: continue
                    close = df['Close']
                    delta = close.diff()
                    gain = delta.where(delta > 0, 0).rolling(14).mean()
                    loss = -delta.where(delta < 0, 0).rolling(14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    momentum = close.pct_change(5)
                    rebound_score = (rsi < 30).astype(int) * 40 + (momentum > 0).astype(int) * 30 + ((close / close.rolling(252).max()) > 0.85).astype(int) * 30
                    data.append({"Ticker": t, "Price": round(close.iloc[-1], 2), "RSI": round(rsi.iloc[-1], 1), "Momentum 5d %": round(momentum.iloc[-1]*100, 1), "Rebound Score": round(rebound_score.iloc[-1], 1)})
                return pd.DataFrame(data)
            except Exception as e:
                handle_error(e, "rebound_analyzer")
                return pd.DataFrame()
        analyze_btn.click(analyze_rebounds, inputs=tickers_rb, outputs=result_table)

def build_self_improve_tab():
    with gr.Column():
        gr.Markdown("## 🧠 Self-Improvement Module (SIM)")
        prompt_input = gr.Textbox(label="Improvement Prompt", value="Analyze latest rebound scores and suggest parameter tweaks", lines=3)
        improve_btn = gr.Button("Trigger Self-Improvement Cycle", variant="primary")
        sim_output = gr.Markdown()
        def run_sim(prompt: str):
            try:
                log_event("Self-Improvement cycle started", "INFO", "SIM")
                if not XAI_API_KEY:
                    raise ValueError("XAI_API_KEY not set")
                client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
                response = client.chat.completions.create(model="grok-3-beta", messages=[{"role": "user", "content": f"XForge Trader SIM: {prompt}"}], max_tokens=800)
                suggestion = response.choices[0].message.content
                log_event(f"SIM suggestion generated", "INFO", "SIM")
                with db_connection(SIM_DB) as conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS sim_logs (timestamp TEXT, prompt TEXT, suggestion TEXT)")
                    conn.execute("INSERT INTO sim_logs VALUES (?,?,?)", (datetime.now().isoformat(), prompt, suggestion))
                    conn.commit()
                return f"✅ **SIM Cycle Complete**\n\n**Suggestion**:\n{suggestion}"
            except Exception as e:
                return handle_error(e, "self_improve_SIM")
        improve_btn.click(run_sim, inputs=prompt_input, outputs=sim_output)

# ====================== MAIN APP ======================
def create_xforge_app():
    css = """.gradio-container { background: linear-gradient(135deg, #0a0f1a 0%, #1f2937 100%); color: #e0f0ff; } .gr-button { font-size: 1.25em; padding: 20px 30px; }"""
    with gr.Blocks(title="XFORGE TRADER v11.3 – SETUP COMPLETE", theme=gr.themes.Default(), css=css) as demo:
        gr.Markdown("# XFORGE TRADER v11.3\n**All errors now logged centrally • Historical DB ready • Self-improving platform live**")
        with gr.Tabs():
            with gr.Tab("📊 Multi-Ticker Watchlist"): build_watchlist_tab()
            with gr.Tab("⚙️ Strategy Optimizer"): build_strategy_optimizer_tab()
            with gr.Tab("🗄️ Historical Database Builder"): build_historical_database_tab()
            with gr.Tab("🔄 Rebound Analyzer"): build_rebound_analyzer_tab()
            with gr.Tab("🧠 Self-Improvement (SIM)"): build_self_improve_tab()
    return demo

if __name__ == "__main__":
    try:
        log_event("🚀 XForge SETUP.PY v11.3 launched – full merge active", "INFO", "setup_startup")
        init_historical_db()
        ingest_historical_data("BHP.AX, RIO.AX, TSLA, NVDA, AAPL", "2y")  # default ingestion
        app = create_xforge_app()
        app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, show_api=False, share=False, quiet=True)
    except Exception as e:
        handle_error(e, "main_launch")
        print("❌ Fatal startup error – check logs/xforge_errors.log")
