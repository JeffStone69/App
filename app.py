from flask import Flask, render_template_string
import os
from ib_insync import *
import time
import threading

app = Flask(__name__)

# Simple home page
HTML = """
<!DOCTYPE html>
<html>
<head><title>XForge Trader</title></head>
<body>
    <h1>✅ XForge Trader is Running</h1>
    <p>IBKR Connection Test: Check terminal for AUD/USD data and test order.</p>
    <p><a href="/status">Check Status</a></p>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/status")
def status():
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=999, timeout=5)
        contract = Forex("AUDUSD")
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract)
        ib.sleep(2)
        price = f"Bid: {ticker.bid:.5f} | Ask: {ticker.ask:.5f}"
        ib.disconnect()
        return f"<h1>✅ Connected to IBKR Paper</h1><p>{price}</p>"
    except Exception as e:
        return f"<h1>❌ IBKR Error</h1><p>{str(e)}</p>"

if __name__ == "__main__":
    print("🚀 Starting XForge Trader...")
    # Run IB test in background
    def ib_test():
        time.sleep(3)
        print("📡 Testing IBKR connection...")
        try:
            ib = IB()
            ib.connect("127.0.0.1", 7497, clientId=998)
            contract = Forex("AUDUSD")
            ib.qualifyContracts(contract)
            ticker = ib.reqMktData(contract)
            print("📈 Live AUD/USD streaming started")
            ib.sleep(5)
            ib.disconnect()
        except Exception as e:
            print(f"IBKR test failed: {e}")
    
    threading.Thread(target=ib_test, daemon=True).start()
    
    app.run(host="0.0.0.0", port=5000, debug=False)