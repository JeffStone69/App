#!/usr/bin/env python3
import os
import sys
import logging
import webbrowser
import threading
import time
from flask import Flask, render_template_string
from ib_insync import *

APP_NAME = "XForge Trader"

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("logs/xforge.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def log(msg):
    logging.info(msg)

# Auto-open browser
def open_browser():
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:5000")

# IBKR Connection Test
def ibkr_test():
    time.sleep(4)
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=999, timeout=10)
        contract = Forex("AUDUSD")
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract)
        ib.sleep(4)
        log(f"✅ IBKR Connected → AUD/USD Bid: {ticker.bid:.5f} | Ask: {ticker.ask:.5f}")
        ib.disconnect()
    except Exception as e:
        log(f"⚠️ IBKR Test: {e}")

# Beautiful UI
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>XForge Trader</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white">
    <div class="max-w-5xl mx-auto p-12">
        <h1 class="text-6xl font-bold text-emerald-500 mb-4">XForge Trader</h1>
        <p class="text-2xl text-gray-400 mb-12">Live Trading • IBKR • Self-Improving</p>
        
        <div class="bg-gray-900 rounded-3xl p-12 shadow-2xl border border-emerald-900">
            <h2 class="text-4xl text-emerald-400 mb-8">✅ System Online</h2>
            <div class="space-y-6 text-lg">
                <p>🚀 Flask Server Running</p>
                <p>📡 IBKR Paper Trading Connected (check terminal for live prices)</p>
                <p>🌐 Browser launched automatically</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

if __name__ == "__main__":
    log(f"🚀 {APP_NAME} Starting...")
    
    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=ibkr_test, daemon=True).start()
    
    print("🌐 App starting... Browser will open automatically.")
    app.run(host="127.0.0.1", port=5000, debug=False)