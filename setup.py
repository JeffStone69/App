#!/usr/bin/env python3
"""
Elite Quant FULLY AUTOMATED Historical + LIVE Data Pipeline
One-file bootstrap + production engine | Python 3.12+
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
    """Perform EVERY setup task automatically."""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # 1. requirements.txt
    with open("requirements.txt", "w") as f:
        f.write("""yfinance
pandas
sqlalchemy
psycopg2-binary
python-dotenv
tqdm
ib_insync
""")

    # 2. .env.example + .env
    with open(".env.example", "w") as f:
        f.write("""DB_URL=sqlite:///quant_historical.db
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=999
""")
    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("✅ .env created (copy of .env.example)")

    # 3. .gitignore
    with open(".gitignore", "w") as f:
        f.write("""__pycache__/
*.pyc
.env
logs/
backups/
*.db
.DS_Store
data/
""")

    # 4. Git initialisation + commit
    if not os.path.exists(".git"):
        subprocess.run(["git", "init"], check=True, capture_output=True)
        print("✅ Git repository initialised")

    subprocess.run(["git", "add", "."], check=True, capture_output=True)

    try:
        subprocess.run(["git", "commit", "-m", "v2.3: Full automated Elite Quant pipeline + live IBKR"], check=True, capture_output=True)
        print("✅ Changes committed")
    except subprocess.CalledProcessError:
        print("✅ No new changes to commit")

    # 5. Push to GitHub
    if repo_url:
        remotes = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True).stdout
        if "origin" not in remotes:
            subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
            print(f"✅ Remote origin added → {repo_url}")
        subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
        print("🚀 Pushed to GitHub successfully!")
    else:
        print("💡 Run with --push and --repo-url https://github.com/JeffStone69/YOUR_REPO.git for auto-push")

    print("🎉 FULL PROJECT BOOTSTRAP COMPLETE — ready for production")

# ========================= CONFIG & LOGGING =========================
load_dotenv()

DEFAULT_TICKERS = ["AAPL", "TSLA", "NVDA", "SPY", "MSFT", "GOOGL", "AMZN", "META", "QQQ"]
DB_URL = os.getenv("DB_URL", "sqlite:///quant_historical.db")
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", 7497))
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", 999))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/quant_{datetime.now().strftime('%Y%m%d')}.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)

engine = create_engine(DB_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)

# ========================= DB & IB =========================
def init_database():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS price_history (
                ticker TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume BIGINT, adj_close REAL,
                PRIMARY KEY (ticker, timestamp)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ticker_ts ON price_history(ticker, timestamp);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ts ON price_history(timestamp);"))
        conn.commit()
    logger.info(f"✅ Database ready → {DB_URL}")

def get_latest_timestamp(ticker: str) -> Optional[datetime]:
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT MAX(timestamp) FROM price_history WHERE ticker = :ticker"), {"ticker": ticker}).scalar()
            return res
    except:
        return None

# ========================= FIXED HISTORICAL FETCH =========================
def fetch_historical(ticker: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    try:
        latest = None if force_refresh else get_latest_timestamp(ticker)
        
        if latest and not force_refresh:
            start_date = (latest + timedelta(days=1)).strftime("%Y-%m-%d")
            data = yf.download(ticker, start=start_date, interval="1d",
                               auto_adjust=True, progress=False, threads=True)
        else:
            data = yf.download(ticker, period="max", interval="1d",
                               auto_adjust=True, progress=False, threads=True)

        if data.empty:
            logger.warning(f"No new data for {ticker}")
            return None

        data.reset_index(inplace=True)

        # ROBUST COLUMN FIX (eliminates ['adj_close'] not in index forever)
        data.rename(columns=str.lower, inplace=True)
        col_map = {}
        for c in data.columns:
            if "open" in c: col_map[c] = "open"
            elif "high" in c: col_map[c] = "high"
            elif "low" in c: col_map[c] = "low"
            elif "close" in c and "adj" not in c: col_map[c] = "close"
            elif "adj" in c or "adjusted" in c: col_map[c] = "adj_close"
            elif "volume" in c: col_map[c] = "volume"
            elif "date" in c or "datetime" in c: col_map[c] = "timestamp"
        data.rename(columns=col_map, inplace=True)

        for col in ["open", "high", "low", "close", "volume"]:
            if col not in data.columns:
                data[col] = None if col != "volume" else 0
        if "adj_close" not in data.columns:
            data["adj_close"] = data["close"]

        data["ticker"] = ticker
        data = data[["ticker", "timestamp", "open", "high", "low", "close", "volume", "adj_close"]]
        data = data.dropna(subset=["timestamp"])

        logger.info(f"✅ Fetched {len(data):,} new rows for {ticker}")
        return data
    except Exception as e:
        logger.error(f"yfinance failed for {ticker}: {e}")
        return None

def upsert_data(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    try:
        # Backup before write
        shutil.copy(DB_URL.split("///")[-1], f"backups/quant_historical_{datetime.now().strftime('%Y%m%d_%H%M')}.db")
        df.to_sql('price_history', engine, if_exists='append', index=False, method='multi', chunksize=2000)
        logger.info(f"✅ Upserted {len(df):,} rows for {df['ticker'].iloc[0]}")
        return len(df)
    except Exception as e:
        logger.error(f"DB upsert error: {e}")
        return 0

# ========================= LIVE IBKR =========================
ib = None
try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

def start_ib() -> bool:
    global ib
    if not IB_AVAILABLE:
        logger.error("ib_insync not installed. Run --install first.")
        return False
    try:
        ib = IB()
        ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=15)
        logger.info("✅ Connected to IBKR TWS/Gateway")
        return True
    except Exception as e:
        logger.error(f"IBKR connection failed: {e}")
        return False

async def subscribe_live(tickers: List[str]):
    if not start_ib():
        return
    contracts = [Stock(t, 'SMART', 'USD') for t in tickers]
    contracts = ib.qualifyContracts(*contracts)
    for contract in contracts:
        ib.reqMktData(contract, '', False, False)
        logger.info(f"📡 Live subscription active: {contract.symbol}")

    def on_tick(tick):
        logger.info(f"LIVE | {tick.contract.symbol} | Last={getattr(tick, 'last', 'N/A')} | Bid={getattr(tick, 'bid', 'N/A')} | Ask={getattr(tick, 'ask', 'N/A')}")

    ib.pendingTickersEvent += on_tick
    await ib.sleep(3600)  # keep alive 1 hour (adjust as needed)

# ========================= MAIN PIPELINE =========================
def build_database(tickers: List[str], force_refresh: bool = False):
    init_database()
    logger.info(f"🚀 Incremental historical build for {len(tickers)} tickers...")
    for ticker in tqdm(tickers, desc="Historical"):
        df = fetch_historical(ticker, force_refresh)
        if df is not None:
            upsert_data(df)
    logger.info("🎉 Historical database synced!")

def main():
    parser = argparse.ArgumentParser(description="Elite Quant FULL AUTO Pipeline")
    parser.add_argument("--bootstrap", action="store_true", help="Run full project setup + git push")
    parser.add_argument("--install", action="store_true", help="Install all dependencies")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--live", action="store_true", help="Start live IBKR feed")
    parser.add_argument("--push", action="store_true", help="Push to GitHub")
    parser.add_argument("--repo-url", type=str, default=None, help="GitHub repo URL (e.g. https://github.com/JeffStone69/APP.git)")
    args = parser.parse_args()

    if args.bootstrap:
        bootstrap_project(args.repo_url)
        if args.install:
            print("Installing dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ All dependencies installed")

    if args.install and not args.bootstrap:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed")

    build_database(args.tickers, args.force)

    if args.live:
        import asyncio
        asyncio.run(subscribe_live(args.tickers))

if __name__ == "__main__":
    main()