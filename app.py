#!/usr/bin/env python3
import os
import sys
import json
import logging
import traceback
import sqlite3
import webbrowser
import threading
import time
from datetime import datetime

import pandas as pd
import yfinance as yf
from flask import Flask, request, render_template_string, redirect, url_for, flash
from openai import OpenAI
from ib_insync import *

APP_NAME = "XForge Trader"
LOG_FILE = "logs/xforge_errors.log"
CONFIG_FILE = "config.json"
BACKUP_DIR = "backups"
DEFAULT_MODEL = "grok-4"

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ====================== LOGGING ======================
def setup_logging():
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

def log_event(message, level="INFO"):
    getattr(logger, level.lower(), logger.info)(message)

def handle_error(e, context=""):
    tb = traceback.format_exc()
    log_event(f"ERROR in {context}: {str(e)}\n{tb}", "ERROR")
    return f"Error in {context}: {str(e)}"

# ====================== CONFIG ======================
def load_config():
    defaults = {
        "xai_api_key": "",
        "github_token": "",
        "db_locations": {"stock_history": "data/stock_history.db", "xforge_historical": "data/xforge_historical.db"},
        "auto_backup_on_sim": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for k, v in defaults.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception:
            return defaults
    return defaults

config = load_config()

# Create folders
for d in ["data", "logs", "backups", "Modules"]:
    os.makedirs(d, exist_ok=True)

# ====================== IBKR TEST ======================
def ibkr_test():
    time.sleep(2)
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=999, timeout=8)
        contract = Forex("AUDUSD")
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract)
        ib.sleep(3)
        log_event(f"IBKR Connected - AUD/USD Bid: {ticker.bid:.5f}")
        ib.disconnect()
    except Exception as e:
        log_event(f"IBKR Test: {e}", "WARNING")

# ====================== HTML UI ======================
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>XForge Trader</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white">
    <div class="max-w-6xl mx-auto p-8">
        <h1 class="text-5xl font-bold text-emerald-400 mb-2">XForge Trader</h1>
        <p class="text-gray-400 mb-8">Self-Improving Trading Platform • IBKR Ready</p>
        
        <div class="bg-gray-800 rounded-2xl p-8">
            <h2 class="text-2xl mb-6 text-emerald-400">Status</h2>
            <p class="text-lg">✅ Flask server running</p>
            <p class="text-lg">📡 IBKR Paper Trading connected (check terminal)</p>
            <p class="text-lg mt-4">Open browser automatically on launch</p>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

# ====================== MAIN ======================
if __name__ == "__main__":
    log_event(f"{APP_NAME} starting up...")

    # Auto open browser
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    # Run IBKR test in background
    threading.Thread(target=ibkr_test, daemon=True).start()

    log_event("Browser should open automatically. If not, go to http://127.0.0.1:5000")
    
    app.run(host="127.0.0.1", port=5000, debug=False)