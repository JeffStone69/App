cd /Users/jeff/Downloads/XAi/GIT/Xapp/App

cat > modules/SIM.py << 'PYEOF'
import gradio as gr, yfinance as yf, pandas as pd, sqlite3, os, logging, matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
LOGS = os.path.join(BASE, "logs")
os.makedirs(DATA, exist_ok=True); os.makedirs(LOGS, exist_ok=True)

DB = os.path.join(DATA, "stock_history.db")
XDB = os.path.join(DATA, "xforge_historical.db")
LOG = os.path.join(LOGS, "xforge_errors.log")

logging.basicConfig(filename=LOG, level=logging.ERROR, format='%(asctime)s - %(message)s')
def log(msg): logging.error(msg)

FAV = ["AAPL", "TSLA", "GOOGL", "AMZN", "MSFT", "NVDA"]

def init():
    for d in [DB, XDB]:
        c = sqlite3.connect(d)
        c.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, close REAL, volume INTEGER)')
        c.commit(); c.close()

# ====================== ENHANCED LIVE TICKERS ======================
def get_live_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="30d")
    info = ticker.info
    price = info.get("currentPrice") or hist["Close"].iloc[-1]
    return price, hist

def live():
    results = []
    charts = []
    momentum = []
    risk = []
    
    for sym in FAV:
        try:
            price, hist = get_live_data(sym)
            results.append({"Symbol": sym, "Price": round(price, 2), "Time": datetime.now().strftime("%H:%M:%S")})
            
            # Price Chart
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(hist.index, hist["Close"], label="Price", color="blue")
            ax.set_title(f"{sym} - 30 Day Price")
            ax.legend()
            plt.tight_layout()
            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            charts.append((sym, buf))
            plt.close()
            
            # Momentum (5-day vs 20-day MA)
            hist["MA5"] = hist["Close"].rolling(5).mean()
            hist["MA20"] = hist["Close"].rolling(20).mean()
            signal = "BUY" if hist["MA5"].iloc[-1] > hist["MA20"].iloc[-1] else "SELL"
            momentum.append({"Symbol": sym, "Signal": signal, "MA5": round(hist["MA5"].iloc[-1], 2), "MA20": round(hist["MA20"].iloc[-1], 2)})
            
            # Risk Analysis
            returns = hist["Close"].pct_change().dropna()
            vol = returns.std() * (252**0.5) * 100  # Annualized volatility
            peak = hist["Close"].cummax()
            drawdown = ((hist["Close"] - peak) / peak).min() * 100
            risk.append({"Symbol": sym, "Volatility %": round(vol, 2), "Max Drawdown %": round(drawdown, 2)})
            
        except Exception as e:
            log(str(e))
            results.append({"Symbol": sym, "Price": "N/A", "Time": "Error"})
            momentum.append({"Symbol": sym, "Signal": "Error", "MA5": "-", "MA20": "-"})
            risk.append({"Symbol": sym, "Volatility %": "-", "Max Drawdown %": "-"})
    
    return pd.DataFrame(results), charts, pd.DataFrame(momentum), pd.DataFrame(risk)

# ====================== REST OF THE APP (unchanged) ======================
def fetch(sym, per="1y"):
    try:
        h = yf.Ticker(sym).history(period=per)
        if h.empty: return "No data", None
        c = sqlite3.connect(DB)
        df = h.reset_index()[["Date","Close","Volume"]]; df["symbol"] = sym
        df.columns = ["date","close","volume","symbol"]
        df.to_sql("history", c, if_exists="append", index=False); c.close()
        return f"Saved {len(h)} rows", df
    except Exception as e: log(str(e)); return str(e), None

def hist(sym, lim=100):
    c = sqlite3.connect(DB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{sym}' ORDER BY date DESC LIMIT {lim}", c)
    c.close(); return df

def ship_cost(sym, qty):
    try:
        v = yf.Ticker(sym).history(period="5d")["Volume"].iloc[-1]
        cost = round(v * 0.00001 * qty, 2)
        return f"Shipping {sym} × {qty} → Est. cost: ${cost}"
    except Exception as e: log(str(e)); return str(e)

def sim_hist(sym, days=30):
    c = sqlite3.connect(DB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{sym}' ORDER BY date DESC LIMIT {days}", c)
    c.close()
    if df.empty: return "No data"
    df["MA"] = df["close"].rolling(5).mean()
    sig = "BUY" if df["close"].iloc[-1] > df["MA"].iloc[-1] else "SELL"
    return f"SIM → {sig} signal for {sym}"

def forge(sym):
    return live()[0][live()[0]["Symbol"]==sym], ship_cost(sym, 100), hist(sym, 20)

def xforge(sym):
    c = sqlite3.connect(XDB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{sym}' LIMIT 100", c)
    c.close(); return df if not df.empty else pd.DataFrame({"msg":["No data"]})

def errors():
    try: return open(LOG).read()[-3000:]
    except: return "No errors yet"

def update_forge():
    os.system("python3 -c 'import yfinance as yf; print(\"Forge updated\")'"); return "✅ Forge DB refreshed"

init()
with gr.Blocks(title="XForge Trader v9.2") as app:
    gr.Image(os.path.join(BASE, "logo.jpg"), height=100, show_label=False)
    gr.Markdown("# XForge Trader – Complete Dashboard")
    
    # ====================== ENHANCED LIVE TICKERS TAB ======================
    with gr.Tab("🔥 Live Tickers"):
        gr.Markdown("### Multi-View Live Dashboard (Prices + Charts + Momentum + Risk)")
        btn = gr.Button("Refresh All Data", variant="primary")
        live_table = gr.Dataframe()
        charts_out = gr.Gallery(label="30-Day Price Charts", columns=3, height=200)
        momentum_df = gr.Dataframe(label="Momentum (MA Crossover)")
        risk_df = gr.Dataframe(label="Risk Analysis")
        btn.click(live, None, [live_table, charts_out, momentum_df, risk_df])

    with gr.Tab("📈 Fetch & Store"):
        s=gr.Textbox("AAPL"); p=gr.Dropdown(["1y","5y"],value="1y")
        gr.Button("Fetch").click(fetch, [s,p], [gr.Textbox(), gr.Dataframe()])
    with gr.Tab("📊 History"): gr.Button("Show").click(hist, [gr.Textbox("AAPL"), gr.Slider(10, 500, value=100, step=10)], gr.Dataframe())
    with gr.Tab("🚚 Shipping+Cost"): gr.Button("Calculate").click(ship_cost, [gr.Textbox("AAPL"), gr.Number(100)], gr.Textbox())
    with gr.Tab("🧠 SIM on History"): gr.Button("Run SIM").click(sim_hist, [gr.Textbox("AAPL"), gr.Slider(10, 100, value=30, step=5)], gr.Textbox())
    with gr.Tab("🚀 Forge Dashboard"): gr.Button("Load All").click(forge, gr.Textbox("AAPL"), [gr.Dataframe(), gr.Textbox(), gr.Dataframe()])
    with gr.Tab("🗄️ XForge DB"): gr.Button("Query").click(xforge, gr.Textbox("AAPL"), gr.Dataframe())
    with gr.Tab("⚠️ Errors"): gr.Button("View Log").click(errors, None, gr.Textbox(lines=12))
    with gr.Tab("🔄 Update Forge"): gr.Button("Update Now").click(update_forge, None, gr.Textbox())

app.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())
PYEOF

echo "✅ Live Tickers tab fully upgraded with graphs, momentum & risk analysis."
echo "Run: ./launch.command"
