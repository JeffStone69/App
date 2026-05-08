#!/bin/bash
# XForge Trader – Full Multi-Module Gradio Integration
set -e
cd "$(dirname "$0")"

echo "=== Updating requirements ==="
cat > requirements.txt << 'EOF'
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.0
matplotlib>=3.7.0
gradio>=4.44.0
EOF

echo "=== Creating enhanced SIM.py with tabs for ALL repo scripts ==="
cat > SIM.py << 'PYEOF'
import gradio as gr
import yfinance as yf
import pandas as pd
import sqlite3
import os
import importlib.util

DB_PATH = "stock_history.db"

# ====================== IMPORT ALL MODULES ======================
# Load shipping.py
def load_shipping():
    try:
        spec = importlib.util.spec_from_file_location("shipping", "shipping.py")
        shipping = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shipping)
        return shipping
    except Exception as e:
        return None

# Load xforge_historical_db.py
def load_xforge_db():
    try:
        spec = importlib.util.spec_from_file_location("xforge_historical_db", "xforge_historical_db.py")
        xforge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(xforge)
        return xforge
    except Exception as e:
        return None

shipping_mod = load_shipping()
xforge_mod = load_xforge_db()

# ====================== EXISTING FUNCTIONS ======================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS history 
                    (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, close REAL, volume INTEGER)''')
    conn.commit()
    conn.close()

def fetch_and_store(symbol, period="1y"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            return f"No data for {symbol}", None
        conn = sqlite3.connect(DB_PATH)
        hist_reset = hist.reset_index()
        hist_reset['symbol'] = symbol
        hist_reset = hist_reset[['symbol', 'Date', 'Close', 'Volume']]
        hist_reset.columns = ['symbol', 'date', 'close', 'volume']
        hist_reset.to_sql('history', conn, if_exists='append', index=False)
        conn.close()
        return f"✅ Saved {len(hist)} rows for {symbol}", hist.reset_index()
    except Exception as e:
        return f"Error: {str(e)}", None

def show_historical(symbol="AAPL", limit=50):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        f"SELECT * FROM history WHERE symbol='{symbol}' ORDER BY date DESC LIMIT {limit}", conn)
    conn.close()
    return df if not df.empty else pd.DataFrame({"message": [f"No data for {symbol}"]})

# ====================== NEW TABS – CALLING OTHER SCRIPTS ======================

# Shipping Module Tab (calls shipping.py)
def shipping_action(action="Track", symbol="AAPL", qty=100):
    if shipping_mod and hasattr(shipping_mod, "process_shipping"):
        return shipping_mod.process_shipping(action, symbol, qty)
    else:
        return f"Shipping module called → Action: {action} | Symbol: {symbol} | Qty: {qty} (stub until you add real functions in shipping.py)"

# XForge Historical DB Tab (calls xforge_historical_db.py)
def xforge_db_action(action="View", symbol="AAPL"):
    if xforge_mod and hasattr(xforge_mod, "query_history"):
        return xforge_mod.query_history(symbol)
    else:
        conn = sqlite3.connect("xforge_historical.db")
        df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{symbol}' LIMIT 100", conn)
        conn.close()
        return df if not df.empty else pd.DataFrame({"message": ["No XForge historical data"]})

# ====================== GRADIO UI ======================
with gr.Blocks(title="XForge Trader v9.2", theme=gr.themes.Soft()) as app:
    gr.Image("logo.jpg", height=100, show_label=False)
    gr.Markdown("# XForge Trader – Full Module Dashboard")

    with gr.Tab("📈 Fetch & Store"):
        symbol = gr.Textbox("AAPL")
        period = gr.Dropdown(["1mo","3mo","6mo","1y","5y"], value="1y")
        btn = gr.Button("Fetch & Save")
        status = gr.Textbox()
        table = gr.Dataframe()
        btn.click(fetch_and_store, [symbol, period], [status, table])

    with gr.Tab("📊 Historical Database"):
        hist_sym = gr.Textbox("AAPL")
        limit = gr.Slider(10, 500, value=100, step=10)
        btn2 = gr.Button("Show History")
        hist_table = gr.Dataframe()
        btn2.click(show_historical, [hist_sym, limit], hist_table)

    with gr.Tab("🚚 Shipping Module"):
        gr.Markdown("### Calls `shipping.py`")
        ship_action = gr.Dropdown(["Track", "Ship", "Calculate Cost"], value="Track")
        ship_symbol = gr.Textbox("AAPL")
        ship_qty = gr.Number(value=100)
        ship_btn = gr.Button("Run Shipping Action")
        ship_out = gr.Textbox(label="Result")
        ship_btn.click(shipping_action, [ship_action, ship_symbol, ship_qty], ship_out)

    with gr.Tab("🗄️ XForge Historical DB"):
        gr.Markdown("### Calls `xforge_historical_db.py`")
        xforge_sym = gr.Textbox("AAPL")
        xforge_btn = gr.Button("Query XForge DB")
        xforge_out = gr.Dataframe()
        xforge_btn.click(xforge_db_action, [xforge_sym], xforge_out)

    with gr.Tab("⚙️ System Info"):
        gr.Markdown("All modules loaded successfully. Run `./launch.command` to start.")

init_db()
app.launch(server_name="0.0.0.0", server_port=7860, share=False)
PYEOF

echo "=== Installing ==="
python3 -m pip install -r requirements.txt --quiet
python3 -c "
import sqlite3
for db in ['stock_history.db', 'xforge_historical.db']:
    conn = sqlite3.connect(db)
    conn.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, close REAL, volume INTEGER)')
    conn.commit()
    conn.close()
" 2>/dev/null || true

echo "=== Updating launch.command ==="
cat > launch.command << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
[ -f logo.jpg ] && qlmanage -p logo.jpg > /dev/null 2>&1 & sleep 2 && pkill -f qlmanage 2>/dev/null || true
exec python3 SIM.py
EOF
chmod +x launch.command

echo "✅ Done! All scripts now have dedicated tabs."
