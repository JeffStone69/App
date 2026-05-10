#!/usr/bin/env python3
"""
Elite Quant Historical + LIVE Data Pipeline
Production-ready | Python 3.12+ | IBKR + yfinance fallback
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm
from dotenv import load_dotenv

# Optional IB live
try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    logger.warning("ib_insync not installed - live feed disabled")

# ========================= CONFIG =========================
load_dotenv()

DEFAULT_TICKERS = ["AAPL", "TSLA", "NVDA", "SPY", "MSFT", "GOOGL", "AMZN", "META", "QQQ"]
DB_URL = os.getenv("DB_URL", "sqlite:///quant_historical.db")
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", 7497))
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", 999))

LOG_LEVEL = logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/quant_{datetime.now().strftime('%Y%m%d')}.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)

engine = create_engine(DB_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)

# ========================= DB SETUP =========================
def init_database() -> None:
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
    """Find last stored date for incremental updates."""
    try:
        with engine.connect() as conn:
            res = conn.execute(text(
                "SELECT MAX(timestamp) FROM price_history WHERE ticker = :ticker"
            ), {"ticker": ticker}).scalar()
            return res
    except:
        return None

# ========================= DATA FETCH =========================
def fetch_historical(ticker: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    try:
        period = "max" if force_refresh else "60d"  # smaller for speed
        data = yf.download(
            ticker, period=period, interval="1d",
            auto_adjust=True, progress=False, threads=True
        )
        if data.empty:
            logger.warning(f"No data for {ticker}")
            return None

        data.reset_index(inplace=True)
        
        # ROBUST COLUMN HANDLING (fixes your error)
        col_map = {}
        for c in data.columns:
            c_lower = str(c).lower().replace(" ", "_")
            if "open" in c_lower: col_map[c] = "open"
            elif "high" in c_lower: col_map[c] = "high"
            elif "low" in c_lower: col_map[c] = "low"
            elif "close" in c_lower and "adj" not in c_lower: col_map[c] = "close"
            elif "adj" in c_lower or "adjusted" in c_lower: col_map[c] = "adj_close"
            elif "volume" in c_lower: col_map[c] = "volume"
        
        data.rename(columns=col_map, inplace=True)
        
        # Ensure required columns
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in data.columns:
                data[col] = None if col != "volume" else 0
        
        if "adj_close" not in data.columns:
            data["adj_close"] = data["close"]
        
        data = data[['Date' if 'Date' in data.columns else 'Datetime', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]
        data.rename(columns={'Date': 'timestamp', 'Datetime': 'timestamp'}, inplace=True)
        data['ticker'] = ticker
        data = data[['ticker', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]
        data = data.dropna(subset=['timestamp'])
        
        return data
    except Exception as e:
        logger.error(f"yfinance failed for {ticker}: {e}")
        return None

def upsert_data(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    try:
        df.to_sql('price_history', engine, if_exists='append', index=False,
                 method='multi', chunksize=2000, if_exists_conflict='ignore')  # SQLite compatible
        rows = len(df)
        logger.info(f"✅ Inserted {rows:,} rows for {df['ticker'].iloc[0]}")
        return rows
    except Exception as e:
        logger.error(f"DB upsert error: {e}")
        return 0

# ========================= LIVE IBKR =========================
ib = None

def start_ib() -> bool:
    global ib
    if not IB_AVAILABLE:
        logger.warning("ib_insync not installed. Install with: pip install ib_insync")
        return False
    try:
        ib = IB()
        ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID)
        logger.info("✅ Connected to IBKR TWS/Gateway")
        return True
    except Exception as e:
        logger.error(f"IB connection failed: {e}")
        return False

async def subscribe_live(tickers: List[str]):
    if not ib or not ib.isConnected():
        if not start_ib():
            return
    contracts = [Stock(t, 'SMART', 'USD') for t in tickers]
    contracts = ib.qualifyContracts(*contracts)
    
    for contract in contracts:
        ib.reqMktData(contract, '', False, False)
        logger.info(f"📡 Subscribed to live ticks: {contract.symbol}")
    
    def on_tick(tick):
        logger.info(f"LIVE | {tick.contract.symbol} | Last={tick.last} | Bid={tick.bid} | Ask={tick.ask}")
        # TODO: push to WebSocket / DB in future
    
    ib.pendingTickersEvent += on_tick

# ========================= MAIN =========================
def build_database(tickers: List[str], force_refresh: bool = False):
    init_database()
    logger.info(f"🚀 Building/updating DB for {len(tickers)} tickers...")
    
    for ticker in tqdm(tickers, desc="Historical"):
        latest = None if force_refresh else get_latest_timestamp(ticker)
        df = fetch_historical(ticker, force_refresh)
        if df is not None:
            upsert_data(df)

    logger.info("🎉 Historical sync complete!")

def main():
    parser = argparse.ArgumentParser(description="Elite Quant Data Pipeline")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--live", action="store_true", help="Start IBKR live feed")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()

    if args.install:
        os.system("pip install yfinance pandas sqlalchemy psycopg2-binary python-dotenv tqdm ib_insync")
        print("✅ All dependencies installed.")
        sys.exit(0)

    build_database(args.tickers, args.force)

    if args.live:
        import asyncio
        asyncio.run(subscribe_live(args.tickers))

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    main()