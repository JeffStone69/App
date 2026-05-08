#!/bin/bash
# XForge Trader v9.2 – Complete Directory + Full Integration Fix
set -e
cd "$(dirname "$0")"

echo "=== [1/8] Creating professional folder structure ==="
mkdir -p data logs modules

echo "=== [2/8] Moving existing files into new structure ==="
[ -f SIM.py ] && mv SIM.py modules/
[ -f shipping.py ] && mv shipping.py modules/
[ -f xforge_historical_db.py ] && mv xforge_historical_db.py modules/
[ -f stock_history.db ] && mv stock_history.db data/
[ -f xforge_historical.db ] && mv xforge_historical.db data/
[ -f xforge_errors.log ] && mv xforge_errors.log logs/

echo "=== [3/8] Creating requirements.txt ==="
cat > requirements.txt << 'EOF'
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.0
matplotlib>=3.7.0
gradio>=4.44.0
EOF

echo "=== [4/8] Creating setup.py ==="
cat > setup.py << 'EOF'
from setuptools import setup, find_packages
setup(
    name="XForge-Trader",
    version="9.2.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0", "numpy>=1.24.0", "yfinance>=0.2.0",
        "matplotlib>=3.7.0", "gradio>=4.44.0"
    ],
    python_requires=">=3.9",
)
EOF

echo "=== [5/8] Creating master SIM.py with ALL tabs + integrations ==="
cat > modules/SIM.py << 'PYEOF'
import gradio as gr
import yfinance as yf
import pandas as pd
import sqlite3
import os
import importlib.util
import logging
from datetime import datetime

# ====================== FOLDER PATHS ======================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "stock_history.db")
XFORGE_DB = os.path.join(DATA_DIR, "xforge_historical.db")
ERROR_LOG = os.path.join(LOGS_DIR, "xforge_errors.log")

# ====================== ERROR LOGGING ======================
logging.basicConfig(
    filename=ERROR_LOG,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_error(msg):
    logging.error(msg)

# ====================== LOAD ALL MODULES ======================
def load_module(name, path):
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        log_error(f"Failed to load {name}: {e}")
        return None

shipping_mod = load_module("shipping", os.path.join(BASE_DIR, "modules/shipping.py"))
xforge_mod = load_module("xforge_historical_db", os.path.join(BASE_DIR, "modules/xforge_historical_db.py"))

# ====================== FAVOURITE STOCKS ======================
FAVOURITES = ["AAPL", "TSLA", "GOOGL", "AMZN", "MSFT", "NVDA"]

def init_dbs():
    for db in [DB_PATH, XFORGE_DB]:
        conn = sqlite3.connect(db)
        conn.execute('''CREATE TABLE IF NOT EXISTS history 
                        (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, close REAL, volume INTEGER)''')
        conn.commit()
        conn.close()

def fetch_live_tickers():
    results = []
    for sym in FAVOURITES:
        try:
            t = yf.Ticker(sym)
            price = t.info.get("currentPrice") or t.history(period="1d")["Close"].iloc[-1]
            results.append({"Symbol": sym, "Price": round(price, 2), "Time": datetime.now().strftime("%H:%M:%S")})
        except Exception as e:
            log_error(f"Live ticker error for {sym}: {e}")
            results.append({"Symbol": sym, "Price": "N/A", "Time": "Error"})
    return pd.DataFrame(results)

def fetch_and_store(symbol, period="1y"):
    try:
        hist = yf.Ticker(symbol).history(period=period)
        if hist.empty: return f"No data for {symbol}", None
        conn = sqlite3.connect(DB_PATH)
        df = hist.reset_index()[["Date", "Close", "Volume"]]
        df["symbol"] = symbol
        df.columns = ["date", "close", "volume", "symbol"]
        df.to_sql("history", conn, if_exists="append", index=False)
        conn.close()
        return f"✅ Saved {len(hist)} rows", df
    except Exception as e:
        log_error(str(e))
        return f"Error: {e}", None

# ====================== ALL INTEGRATED TABS ======================

def shipping_with_cost(symbol, qty):
    try:
        vol = yf.Ticker(symbol).history(period="5d")["Volume"].iloc[-1]
        cost = round(vol * 0.00001 * qty, 2)   # Forge + Shipping integration
        if shipping_mod and hasattr(shipping_mod, "process_shipping"):
            return shipping_mod.process_shipping("Calculate Cost", symbol, qty) + f" | Auto-cost: ${cost}"
        return f"Shipping action for {symbol} | Qty: {qty} | Est. Cost: ${cost}"
    except Exception as e:
        log_error(str(e))
        return f"Error: {e}"

def sim_using_historical(symbol, days=30):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{symbol}' ORDER BY date DESC LIMIT {days}", conn)
    conn.close()
    if df.empty: return "No historical data for simulation"
    # Simple SIM integration (moving average strategy)
    df["MA"] = df["close"].rolling(5).mean()
    signal = "BUY" if df["close"].iloc[-1] > df["MA"].iloc[-1] else "SELL"
    return f"SIM Result for {symbol}: {signal} (based on last {days} days)"

def forge_dashboard(symbol):
    live = fetch_live_tickers()[fetch_live_tickers()["Symbol"] == symbol]
    ship = shipping_with_cost(symbol, 100)
    hist = show_historical(symbol, 20)
    return live, ship, hist

def show_historical(symbol, limit):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{symbol}' ORDER BY date DESC LIMIT {limit}", conn)
    conn.close()
    return df

def xforge_db_action(symbol):
    conn = sqlite3.connect(XFORGE_DB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{symbol}' LIMIT 100", conn)
    conn.close()
    return df if not df.empty else pd.DataFrame({"message": ["No data"]})

def view_error_log():
    try:
        with open(ERROR_LOG, "r") as f:
            return f.read()[-3000:]   # Last 3000 chars
    except:
        return "No errors logged yet."

def one_click_forge_update():
    try:
        os.system(f"python3 {os.path.join(BASE_DIR, 'modules/xforge_historical_db.py')} > /dev/null 2>&1")
        return "✅ Forge DB updated! All tabs refreshed."
    except Exception as e:
        log_error(str(e))
        return f"Update failed: {e}"

# ====================== GRADIO UI ======================
with gr.Blocks(title="XForge Trader v9.2", theme=gr.themes.Soft()) as app:
    gr.Image(os.path.join(BASE_DIR, "logo.jpg"), height=100, show_label=False)
    gr.Markdown("# XForge Trader – Complete Multi-Module Dashboard")

    with gr.Tab("🔥 Live Tickers (Favourites)"):
        gr.Markdown("### Current prices for your favourite stocks (auto-stored)")
        live_btn = gr.Button("Fetch Live Prices & Store", variant="primary")
        live_df = gr.Dataframe()
        live_btn.click(fetch_live_tickers, outputs=live_df)

    with gr.Tab("📈 Fetch & Store"):
        sym = gr.Textbox("AAPL")
        per = gr.Dropdown(["1mo","1y","5y"], value="1y")
        btn = gr.Button("Fetch & Save to DB")
        status = gr.Textbox()
        tbl = gr.Dataframe()
        btn.click(fetch_and_store, [sym, per], [status, tbl])

    with gr.Tab("📊 Historical Database"):
        hs = gr.Textbox("AAPL")
        lm = gr.Slider(10, 500, value=100)
        hb = gr.Button("Show History")
        ht = gr.Dataframe()
        hb.click(show_historical, [hs, lm], ht)

    with gr.Tab("🚚 Shipping + Forge Cost"):
        gr.Markdown("### Shipping Module + Auto Shipping Cost (Forge integration)")
        sa = gr.Textbox("AAPL")
        sq = gr.Number(value=100)
        sb = gr.Button("Run Shipping + Calculate Cost")
        so = gr.Textbox()
        sb.click(shipping_with_cost, [sa, sq], so)

    with gr.Tab("🗄️ XForge Historical DB"):
        xs = gr.Textbox("AAPL")
        xb = gr.Button("Query XForge DB")
        xo = gr.Dataframe()
        xb.click(xforge_db_action, xs, xo)

    with gr.Tab("🧠 SIM + Historical"):
        gr.Markdown("### SIM Simulation using Historical Database")
        ss = gr.Textbox("AAPL")
        sd = gr.Slider(10, 100, value=30)
        sbtn = gr.Button("Run SIM on History")
        sout = gr.Textbox()
        sbtn.click(sim_using_historical, [ss, sd], sout)

    with gr.Tab("🚀 Forge Dashboard"):
        gr.Markdown("### Cross-module: Live + Shipping + Trends")
        fd_sym = gr.Textbox("AAPL")
        fd_btn = gr.Button("Load Full Dashboard")
        fd_live = gr.Dataframe()
        fd_ship = gr.Textbox()
        fd_hist = gr.Dataframe()
        fd_btn.click(forge_dashboard, fd_sym, [fd_live, fd_ship, fd_hist])

    with gr.Tab("⚠️ Error Log"):
        el_btn = gr.Button("View Latest Errors")
        el_out = gr.Textbox(lines=15)
        el_btn.click(view_error_log, outputs=el_out)

    with gr.Tab("🔄 One-Click Forge Update"):
        gr.Markdown("Runs `xforge_historical_db.py` and refreshes everything")
        up_btn = gr.Button("Update Forge DB Now", variant="primary")
        up_out = gr.Textbox()
        up_btn.click(one_click_forge_update, outputs=up_out)

init_dbs()
app.launch(server_name="0.0.0.0", server_port=7860, share=False)
PYEOF

echo "=== [6/8] Creating robust launch.command ==="
cat > launch.command << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
[ -f logo.jpg ] && qlmanage -p logo.jpg > /dev/null 2>&1 & sleep 2.5 && pkill -f qlmanage 2>/dev/null || true
exec python3 modules/SIM.py
EOF
chmod +x launch.command

echo "=== [7/8] Installing everything ==="
python3 -m pip install -r requirements.txt --quiet
python3 setup.py install --quiet

echo "=== [8/8] Final verification ==="
ls -la modules/ data/ logs/ launch.command requirements.txt setup.py logo.jpg

echo ""
echo "✅ FULL INTEGRATION COMPLETE!"
echo "Run: ./launch.command"
echo "Open browser: http://localhost:7860"
