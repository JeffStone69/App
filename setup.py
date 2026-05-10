#!/usr/bin/env python3
"""
Elite Quant FULLY AUTOMATED Historical + LIVE Data Pipeline
Hotfixed column handling + robust yfinance parsing
"""

import os
import sys
import argparse
import logging
import subprocess
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm
from dotenv import load_dotenv

# ========================= AUTO BOOTSTRAP =========================
def bootstrap_project(repo_url: Optional[str] = None):
    os.makedirs("logs", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    with open("requirements.txt", "w") as f:
        f.write("yfinance\npandas\nsqlalchemy\npsycopg2-binary\npython-dotenv\ntqdm\nib_insync\n")

    with open(".env.example", "w") as f:
        f.write("""DB_URL=sqlite:///quant_historical.db
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=999
""")
    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("✅ .env created")

    with open(".gitignore", "w") as f:
        f.write("__pycache__/\n*.pyc\n.env\nlogs/\nbackups/\n*.db\n.DS_Store\ndata/\n")

    if not os.path.exists(".git"):
        subprocess.run(["git", "init"], check=True, capture_output=True)
        print("✅ Git initialised")

    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    try:
        subprocess.run(["git", "commit", "-m", "v2.4: Hotfix yfinance column mapping + auto bootstrap"], check=True, capture_output=True)
        print("✅ Committed")
    except:
        pass

    if repo_url:
        subprocess.run(["git", "remote", "add", "origin", repo_url], check=False)
        subprocess.run(["git", "branch", "-M", "main"], check=False)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=False)
        print("🚀 Pushed to GitHub")

# ========================= CONFIG =========================
load_dotenv()

DEFAULT_TICKERS = ["AAPL", "TSLA", "NVDA", "SPY", "MSFT", "GOOGL", "AMZN", "META", "QQQ"]
DB_URL = os.getenv("DB_URL", "sqlite:///quant_historical.db")
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", 7497))
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", 999))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(f"logs/quant_{datetime.now().strftime('%Y%m%d')}.log", mode='a')]
)
logger = logging.getLogger(__name__)

engine = create_engine(DB_URL, echo=False, pool_pre_ping=True)

# ========================= DB =========================
def init_database():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS price_history (
                ticker TEXT, timestamp TIMESTAMP,
                open REAL, high REAL, low REAL, close REAL,
                volume BIGINT, adj_close REAL,
                PRIMARY KEY (ticker, timestamp)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ticker_ts ON price_history(ticker, timestamp);"))
        conn.commit()
    logger.info(f"✅ Database ready → {DB_URL}")

def get_latest_timestamp(ticker: str) -> Optional[datetime]:
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT MAX(timestamp) FROM price_history WHERE ticker = :t"), {"t": ticker}).scalar()
            return res
    except:
        return None

# ========================= FIXED FETCH (THIS IS THE FIX) =========================
def fetch_historical(ticker: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    try:
        if not force_refresh:
            latest = get_latest_timestamp(ticker)
            if latest:
                start = (latest + timedelta(days=1)).strftime("%Y-%m-%d")
                data = yf.download(ticker, start=start, interval="1d", auto_adjust=True, progress=False, threads=True)
            else:
                data = yf.download(ticker, period="max", interval="1d", auto_adjust=True, progress=False, threads=True)
        else:
            data = yf.download(ticker, period="max", interval="1d", auto_adjust=True, progress=False, threads=True)

        if data.empty:
            logger.warning(f"No data for {ticker}")
            return None

        # === ROBUST COLUMN FIX ===
        data = data.reset_index()

        # Standardise column names
        data.columns = [str(col).lower().replace(" ", "_") for col in data.columns]

        # Map to our standard names
        rename_dict = {}
        for col in data.columns:
            if "date" in col or "index" in col:
                rename_dict[col] = "timestamp"
            elif "open" in col:
                rename_dict[col] = "open"
            elif "high" in col:
                rename_dict[col] = "high"
            elif "low" in col:
                rename_dict[col] = "low"
            elif "close" in col and "adj" not in col:
                rename_dict[col] = "close"
            elif "adj" in col or "adjusted" in col:
                rename_dict[col] = "adj_close"
            elif "volume" in col:
                rename_dict[col] = "volume"

        data.rename(columns=rename_dict, inplace=True)

        # Guarantee all required columns exist
        for col in ["open", "high", "low", "close", "volume", "adj_close"]:
            if col not in data.columns:
                data[col] = data["close"] if col in ["open", "high", "low", "adj_close"] else 0

        if "timestamp" not in data.columns:
            data["timestamp"] = pd.to_datetime("today")  # fallback (should never hit)

        data["ticker"] = ticker
        data = data[["ticker", "timestamp", "open", "high", "low", "close", "volume", "adj_close"]].copy()

        logger.info(f"✅ Fetched {len(data):,} rows for {ticker}")
        return data

    except Exception as e:
        logger.error(f"yfinance failed for {ticker}: {e}")
        return None

def upsert_data(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    try:
        backup_path = f"backups/quant_historical_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
        if os.path.exists(DB_URL.split("///")[-1]):
            shutil.copy(DB_URL.split("///")[-1], backup_path)
        df.to_sql('price_history', engine, if_exists='append', index=False, method='multi', chunksize=2000)
        logger.info(f"✅ Upserted {len(df):,} rows for {df['ticker'].iloc[0]}")
        return len(df)
    except Exception as e:
        logger.error(f"DB error: {e}")
        return 0

# ========================= LIVE =========================
try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

async def subscribe_live(tickers: List[str]):
    if not IB_AVAILABLE:
        logger.error("ib_insync not installed. Run --install")
        return
    try:
        ib = IB()
        ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=10)
        logger.info("✅ IBKR Connected")
        contracts = [Stock(t, 'SMART', 'USD') for t in tickers]
        contracts = ib.qualifyContracts(*contracts)
        for c in contracts:
            ib.reqMktData(c)
            logger.info(f"📡 Subscribed: {c.symbol}")
        await ib.sleep(3600)
    except Exception as e:
        logger.error(f"Live feed error: {e}")

# ========================= MAIN =========================
def build_database(tickers: List[str], force_refresh: bool = False):
    init_database()
    logger.info(f"🚀 Building historical data for {len(tickers)} tickers...")
    for ticker in tqdm(tickers, desc="Historical"):
        df = fetch_historical(ticker, force_refresh)
        if df is not None:
            upsert_data(df)
    logger.info("🎉 Historical sync complete!")

def main():
    parser = argparse.ArgumentParser(description="Elite Quant Pipeline")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--repo-url", type=str, default=None)
    args = parser.parse_args()

    if args.bootstrap:
        bootstrap_project(args.repo_url)
        if args.install:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencies installed")

    if args.install and not args.bootstrap:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

    build_database(args.tickers, args.force)

    if args.live:
        import asyncio
        asyncio.run(subscribe_live(args.tickers))

if __name__ == "__main__":
    main()