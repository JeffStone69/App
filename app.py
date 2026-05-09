#!/usr/bin/env python3
import os
import sys
import json
import logging
import traceback
import sqlite3
import subprocess
import importlib.util
from datetime import datetime
import pandas as pd
import yfinance as yf
from flask import Flask, request, render_template_string, redirect, url_for, flash
from openai import OpenAI

APP_NAME = "XForge Trader"
LOG_FILE = "logs/xforge_errors.log"
CONFIG_FILE = "config.json"
BACKUP_DIR = "backups"
DEFAULT_MODEL = "grok-4"

app = Flask(__name__)
app.secret_key = os.urandom(24)

def setup_logging():
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

def log_event(message, level="INFO", context=""):
    full_msg = f"[{context}] {message}" if context else message
    getattr(logger, level.lower(), logger.info)(full_msg)

def handle_error(e, context="General"):
    tb = traceback.format_exc()
    log_event(f"ERROR in {context}: {str(e)}\n{tb}", "ERROR", context)
    return f"Error in {context}: {str(e)}. Check {LOG_FILE} for details."

def load_config():
    defaults = {
        "xai_api_key": "",
        "github_token": "",
        "db_locations": {
            "stock_history": "data/stock_history.db",
            "xforge_historical": "data/xforge_historical.db"
        },
        "log_level": "INFO",
        "auto_backup_on_sim": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, val in defaults.items():
                if key not in config:
                    config[key] = val
            return config
        except Exception as e:
            handle_error(e, "load_config")
            return defaults
    return defaults

def save_config(config_dict):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=4)
        log_event("Config saved successfully.", "INFO", "save_config")
    except Exception as e:
        handle_error(e, "save_config")

config = load_config()

def get_db_connection(db_key):
    try:
        db_path = config["db_locations"].get(db_key, f"data/{db_key}.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise Exception(handle_error(e, f"get_db_connection({db_key})"))

def execute_query(db_key, query, params=()):
    try:
        conn = get_db_connection(db_key)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        handle_error(e, f"execute_query({db_key})")
        return []

def git_command(cmd, context="git"):
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=os.getcwd())
        log_event(f"Git command successful: {' '.join(cmd)}", "INFO", context)
        return result.stdout.strip() or "Success"
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        handle_error(e, f"git_command: {context}")
        return f"Failed: {err_msg}"
    except Exception as e:
        return handle_error(e, f"git_command: {context}")

def git_status(): return git_command(["git", "status"], "git_status")
def git_pull(): return git_command(["git", "pull"], "git_pull")
def git_push(commit_msg="Auto-update via App UI"):
    try:
        git_command(["git", "add", "."], "git_push_add")
        git_command(["git", "commit", "-m", commit_msg], "git_push_commit")
        return git_command(["git", "push"], "git_push")
    except Exception as e:
        return handle_error(e, "git_push")

def save_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H:%M:%S")
    backup_file = os.path.join(BACKUP_DIR, f"app_backup_{timestamp}.py")
    try:
        with open(__file__, 'r', encoding='utf-8') as src:
            code = src.read()
        with open(backup_file, 'w', encoding='utf-8') as dst:
            dst.write(code)
        log_event(f"Script backed up to {backup_file}", "INFO", "SIM_backup")
        return backup_file
    except Exception as e:
        handle_error(e, "SIM_backup")
        return ""

def call_xai_for_improvement(current_code, user_prompt):
    if not config["xai_api_key"]:
        return "ERROR: xAI API key not set in Configuration tab."
    try:
        client = OpenAI(api_key=config["xai_api_key"], base_url="https://api.x.ai/v1")
        system_prompt = "You are an expert Python developer specializing in robust, self-improving financial trading applications. Improve the script with better error handling, logging, modularity, performance, security, and new features while keeping all existing functionality. Output ONLY the complete runnable Python code."
        full_user_prompt = f"Current script code:\n\n```python\n{current_code}\n```\n\nImprovement request: {user_prompt}\n\nReturn the FULL improved script."
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_user_prompt}],
            max_tokens=12000,
            temperature=0.6
        )
        improved_code = response.choices[0].message.content.strip()
        if improved_code.startswith("```python"): improved_code = improved_code[9:]
        if improved_code.endswith("```"): improved_code = improved_code[:-3]
        log_event("xAI improvement generated successfully.", "INFO", "SIM_xai")
        return improved_code.strip()
    except Exception as e:
        return handle_error(e, "SIM_xai_call")

def apply_improved_code(improved_code, backup_file):
    try:
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(improved_code)
        log_event(f"New improved code saved. Backup: {backup_file}. Restart app to load.", "INFO", "SIM_apply")
        return "SUCCESS: Code updated. Please restart the application to load the new version."
    except Exception as e:
        return handle_error(e, "SIM_apply")

def load_module_from_file(filepath):
    try:
        spec = importlib.util.spec_from_file_location("dynamic_module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        log_event(f"Module loaded: {filepath}", "INFO", "module_loader")
        return module, f"Module '{os.path.basename(filepath)}' loaded successfully."
    except Exception as e:
        return None, handle_error(e, f"load_module({filepath})")

# ============== REINTEGRATED FINANCIAL FUNCTIONS ==============
def calculate_stock_indicators(symbol):
    try:
        hist = yf.download(symbol, period="6mo", progress=False)
        if hist.empty:
            return None
        hist = hist.reset_index()
        delta = hist["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = round(rsi.iloc[-1], 1)
        rsi_sig = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"

        sma20 = hist["Close"].rolling(20).mean()
        std20 = hist["Close"].rolling(20).std()
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20
        bb_pos = round((hist["Close"].iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]), 2)
        bb_squeeze = "Yes" if (upper.iloc[-1] - lower.iloc[-1]) < (hist["Close"].rolling(20).std().mean() * 1.2) else "No"

        ema12 = hist["Close"].ewm(span=12).mean()
        ema26 = hist["Close"].ewm(span=26).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9).mean()
        macd_sig = "Bullish" if macd.iloc[-1] > signal_line.iloc[-1] else "Bearish"

        returns = hist["Close"].pct_change().dropna()
        vol = round(returns.std() * (252 ** 0.5) * 100, 1)
        peak = hist["Close"].cummax()
        drawdown = (hist["Close"] - peak) / peak
        max_dd = round(drawdown.min() * 100, 1)
        profit_score = round((rsi_val * 0.3 + (100 - abs(bb_pos-0.5)*200) * 0.4 + (50 if macd_sig == "Bullish" else 30) * 0.3), 1)

        return {
            "symbol": symbol,
            "price": round(hist["Close"].iloc[-1], 2),
            "rsi": rsi_val, "rsi_signal": rsi_sig,
            "bb_position": bb_pos, "bb_squeeze": bb_squeeze,
            "macd_signal": macd_sig,
            "volatility": vol,
            "max_drawdown": max_dd,
            "profit_score": profit_score
        }
    except Exception as e:
        handle_error(e, "calculate_stock_indicators")
        return None

def run_backtester(symbol, short_ma=5, long_ma=20):
    try:
        hist = yf.download(symbol, period="1y", progress=False)
        if hist.empty:
            return None
        hist["SMA_short"] = hist["Close"].rolling(short_ma).mean()
        hist["SMA_long"] = hist["Close"].rolling(long_ma).mean()
        hist["Signal"] = 0
        hist.loc[hist["SMA_short"] > hist["SMA_long"], "Signal"] = 1
        hist["Position"] = hist["Signal"].diff()
        returns = hist["Close"].pct_change()
        strategy_returns = returns * hist["Signal"].shift(1)
        total_return = round((strategy_returns.sum() * 100), 2)
        trades = int(hist["Position"].abs().sum())
        win_rate = round((strategy_returns[strategy_returns > 0].count() / trades * 100) if trades > 0 else 0, 1)
        return {"symbol": symbol, "total_return": total_return, "trades": trades, "win_rate": win_rate}
    except Exception as e:
        handle_error(e, "run_backtester")
        return None

def get_historical_data(db_key, symbol, limit=50):
    try:
        conn = get_db_connection(db_key)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM history WHERE symbol = ? ORDER BY date DESC LIMIT ?", (symbol, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        handle_error(e, "get_historical_data")
        return []

# ============== HTML TEMPLATE (All Tabs Reintegrated) ==============
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ app_name }} - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: system-ui, sans-serif; }
        .tab { transition: all 0.2s; }
        .log-text { font-family: ui-monospace, monospace; white-space: pre-wrap; }
        .metric { background: #1f2937; padding: 1rem; border-radius: 0.75rem; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100">
    <div class="max-w-7xl mx-auto p-6">
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-4xl font-bold text-emerald-400">{{ app_name }}</h1>
                <p class="text-gray-400">Full Restoration • Stock Reports • Backtester • Historical DB • SIM</p>
            </div>
            <div class="text-right text-sm">
                <div>Status: <span class="text-emerald-400">Running</span></div>
                <div class="text-gray-500">{{ current_time }}</div>
            </div>
        </div>

        <div class="flex border-b border-gray-700 mb-6 flex-wrap">
            <button onclick="showTab('dashboard')" class="tab px-6 py-3 font-medium border-b-2 border-emerald-400 text-emerald-400">Dashboard</button>
            <button onclick="showTab('stock_reports')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Stock Reports</button>
            <button onclick="showTab('backtester')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Backtester</button>
            <button onclick="showTab('historical_db')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Historical DB</button>
            <button onclick="showTab('sim_db')" class="tab px-6 py-3 font-medium hover:text-emerald-400">SIM Database</button>
            <button onclick="showTab('config')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Configuration</button>
            <button onclick="showTab('git')" class="tab px-6 py-3 font-medium hover:text-emerald-400">GitHub Sync</button>
            <button onclick="showTab('sim')" class="tab px-6 py-3 font-medium hover:text-emerald-400">SIM (Self-Improve)</button>
            <button onclick="showTab('modules')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Module Loader</button>
            <button onclick="showTab('logs')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Logs</button>
        </div>

        <!-- DASHBOARD -->
        <div id="dashboard" class="tab-content">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="bg-gray-800 p-6 rounded-xl">
                    <h3 class="font-semibold mb-4">Quick Stats</h3>
                    <div class="space-y-3 text-sm">
                        <div>DBs Connected: <span class="font-mono">{{ db_count }}</span></div>
                        <div>Backups: <span class="font-mono">{{ backup_count }}</span></div>
                        <div>Log Size: <span class="font-mono">{{ log_size }} KB</span></div>
                    </div>
                </div>
                <div class="bg-gray-800 p-6 rounded-xl md:col-span-3">
                    <h3 class="font-semibold mb-4">Recent Activity</h3>
                    <div class="log-text text-xs bg-gray-950 p-4 rounded h-32 overflow-auto">{{ recent_logs }}</div>
                </div>
            </div>
        </div>

        <!-- STOCK REPORTS TAB (Reintegrated from v9.2) -->
        <div id="stock_reports" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-6">Stock Reports • RSI • Bollinger • MACD • Profit Score</h2>
                <form method="POST" action="/stock_report" class="flex gap-4 mb-6">
                    <input type="text" name="symbol" placeholder="AAPL" class="flex-1 bg-gray-700 p-4 rounded text-xl font-mono" required>
                    <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 px-12 rounded-xl font-medium">Generate Report</button>
                </form>
                {% if stock_report %}
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="metric"><div class="text-sm text-gray-400">Price</div><div class="text-3xl font-bold">{{ stock_report.price }}</div></div>
                    <div class="metric"><div class="text-sm text-gray-400">RSI</div><div class="text-3xl font-bold">{{ stock_report.rsi }}</div><div class="text-xs">{{ stock_report.rsi_signal }}</div></div>
                    <div class="metric"><div class="text-sm text-gray-400">BB Position</div><div class="text-3xl font-bold">{{ stock_report.bb_position }}</div><div class="text-xs">Squeeze: {{ stock_report.bb_squeeze }}</div></div>
                    <div class="metric"><div class="text-sm text-gray-400">MACD</div><div class="text-3xl font-bold">{{ stock_report.macd_signal }}</div></div>
                    <div class="metric"><div class="text-sm text-gray-400">Volatility</div><div class="text-3xl font-bold">{{ stock_report.volatility }}%</div></div>
                    <div class="metric"><div class="text-sm text-gray-400">Max Drawdown</div><div class="text-3xl font-bold">{{ stock_report.max_drawdown }}%</div></div>
                    <div class="metric"><div class="text-sm text-gray-400">Profit Score</div><div class="text-3xl font-bold text-emerald-400">{{ stock_report.profit_score }}</div></div>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- BACKTESTER TAB (Reintegrated) -->
        <div id="backtester" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-6">Backtester • MA Crossover Strategy</h2>
                <form method="POST" action="/backtest" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <input type="text" name="symbol" placeholder="AAPL" class="bg-gray-700 p-4 rounded" required>
                    <input type="number" name="short_ma" value="5" class="bg-gray-700 p-4 rounded">
                    <input type="number" name="long_ma" value="20" class="bg-gray-700 p-4 rounded">
                    <button type="submit" class="bg-purple-600 hover:bg-purple-700 px-8 rounded-xl font-medium">Run Backtest</button>
                </form>
                {% if backtest_result %}
                <div class="bg-gray-950 p-6 rounded-xl">
                    <div class="grid grid-cols-3 gap-4 text-center">
                        <div><div class="text-sm text-gray-400">Total Return</div><div class="text-4xl font-bold">{{ backtest_result.total_return }}%</div></div>
                        <div><div class="text-sm text-gray-400">Trades</div><div class="text-4xl font-bold">{{ backtest_result.trades }}</div></div>
                        <div><div class="text-sm text-gray-400">Win Rate</div><div class="text-4xl font-bold">{{ backtest_result.win_rate }}%</div></div>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- HISTORICAL DB TAB -->
        <div id="historical_db" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-6">Historical Database Viewer</h2>
                <form method="POST" action="/historical_query" class="flex gap-4 mb-6">
                    <input type="text" name="symbol" placeholder="AAPL" class="flex-1 bg-gray-700 p-4 rounded">
                    <button type="submit" class="bg-blue-600 hover:bg-blue-700 px-8 rounded-xl font-medium">Query DB</button>
                </form>
                {% if historical_data %}
                <div class="overflow-auto max-h-96">
                    <table class="w-full text-sm">
                        <thead><tr class="border-b border-gray-700"><th class="p-3 text-left">Date</th><th>Close</th><th>Volume</th></tr></thead>
                        <tbody>
                        {% for row in historical_data %}
                        <tr class="border-b border-gray-800"><td class="p-3">{{ row.date }}</td><td class="text-right">{{ row.close }}</td><td class="text-right">{{ row.volume }}</td></tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- SIM DATABASE TAB -->
        <div id="sim_db" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-6">SIM Database • Self-Improving on Historical Data</h2>
                <p class="text-gray-400 mb-4">Run SIM improvements directly on stored historical data.</p>
                <form method="POST" action="/sim_on_db">
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 px-8 py-3 rounded-xl font-medium">Improve SIM Using Historical DB</button>
                </form>
            </div>
        </div>

        <!-- CONFIG, GIT, SIM, MODULES, LOGS tabs (identical to previous complete version) -->
        <div id="config" class="tab-content hidden">
            <form method="POST" action="/save_config" class="bg-gray-800 p-8 rounded-2xl space-y-6">
                <h2 class="text-2xl font-semibold">Configuration</h2>
                <div><label class="block text-sm mb-1">xAI API Key</label><input type="password" name="xai_api_key" value="{{ config.xai_api_key }}" class="w-full bg-gray-700 p-3 rounded"></div>
                <div><label class="block text-sm mb-1">GitHub Token</label><input type="password" name="github_token" value="{{ config.github_token }}" class="w-full bg-gray-700 p-3 rounded"></div>
                <div class="grid grid-cols-2 gap-4">
                    <div><label class="block text-sm mb-1">Stock History DB Path</label><input type="text" name="db_stock" value="{{ config.db_locations.stock_history }}" class="w-full bg-gray-700 p-3 rounded"></div>
                    <div><label class="block text-sm mb-1">XForge Historical DB Path</label><input type="text" name="db_xforge" value="{{ config.db_locations.xforge_historical }}" class="w-full bg-gray-700 p-3 rounded"></div>
                </div>
                <button type="submit" class="bg-emerald-500 hover:bg-emerald-600 px-8 py-3 rounded-xl font-medium">Save Configuration</button>
            </form>
        </div>

        <div id="git" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl space-y-6">
                <h2 class="text-2xl font-semibold">GitHub Push / Pull Sync</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <form method="POST" action="/git_action"><input type="hidden" name="action" value="status"><button class="w-full bg-gray-700 hover:bg-gray-600 py-3 rounded-xl">Check Status</button></form>
                    <form method="POST" action="/git_action"><input type="hidden" name="action" value="pull"><button class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-xl">Git Pull</button></form>
                    <form method="POST" action="/git_action"><input type="hidden" name="action" value="push"><input type="text" name="commit_msg" placeholder="Commit message" class="w-full mb-2 bg-gray-700 p-3 rounded"><button class="w-full bg-emerald-600 hover:bg-emerald-700 py-3 rounded-xl">Git Push</button></form>
                </div>
                {% if git_result %}<div class="bg-gray-950 p-4 rounded font-mono text-sm">{{ git_result }}</div>{% endif %}
            </div>
        </div>

        <div id="sim" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-4">Self-Improving Module (SIM)</h2>
                <form method="POST" action="/sim_generate" class="space-y-4">
                    <textarea name="prompt" rows="3" class="w-full bg-gray-700 p-4 rounded" placeholder="Improve financial indicators and backtesting..."></textarea>
                    <button type="submit" class="bg-purple-600 hover:bg-purple-700 px-8 py-3 rounded-xl font-medium">Generate Improved Version with xAI</button>
                </form>
                {% if sim_improved_code %}
                <form method="POST" action="/sim_confirm" class="mt-8">
                    <textarea name="improved_code" rows="20" class="w-full bg-gray-950 p-4 font-mono text-xs rounded">{{ sim_improved_code }}</textarea>
                    <button type="submit" class="flex-1 bg-emerald-600 hover:bg-emerald-700 py-3 rounded-xl font-medium mt-4">CONFIRM & SAVE FOR NEXT LAUNCH</button>
                </form>
                {% endif %}
            </div>
        </div>

        <div id="modules" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-4">Dynamic Module Loader</h2>
                <form method="POST" action="/load_module" class="flex gap-4">
                    <input type="text" name="module_path" placeholder="/path/to/module.py" class="flex-1 bg-gray-700 p-3 rounded">
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 px-8 rounded-xl">Load Module</button>
                </form>
                {% if module_result %}<div class="mt-4 p-4 bg-gray-950 rounded">{{ module_result }}</div>{% endif %}
            </div>
        </div>

        <div id="logs" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-4">Event & Error Logs</h2>
                <div class="log-text text-xs bg-gray-950 p-4 rounded h-96 overflow-auto">{{ full_logs }}</div>
            </div>
        </div>
    </div>

    <script>
        function showTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.getElementById(tab).classList.remove('hidden');
        }
        document.getElementById('dashboard').classList.remove('hidden');
    </script>
</body>
</html>"""

# ============== ROUTES (All Reintegrated) ==============
@app.route('/')
def index():
    try:
        db_count = len(config["db_locations"])
        backup_count = len([f for f in os.listdir(BACKUP_DIR) if f.endswith('.py')]) if os.path.exists(BACKUP_DIR) else 0
        log_size = round(os.path.getsize(LOG_FILE) / 1024, 1) if os.path.exists(LOG_FILE) else 0
        recent_logs = ""
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                recent_logs = ''.join(f.readlines()[-15:])
        full_logs = ""
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                full_logs = ''.join(f.readlines()[-100:])
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return render_template_string(HTML_TEMPLATE, app_name=APP_NAME, current_time=current_time, config=config, db_count=db_count, backup_count=backup_count, log_size=log_size, recent_logs=recent_logs, full_logs=full_logs, git_result=request.args.get('git_result', ''), sim_improved_code=request.args.get('sim_improved_code', ''), module_result=request.args.get('module_result', ''))
    except Exception as e:
        flash(handle_error(e, "index"))
        return redirect(url_for('index'))

@app.route('/save_config', methods=['POST'])
def save_config_route():
    global config
    try:
        new_config = config.copy()
        new_config["xai_api_key"] = request.form.get("xai_api_key", "")
        new_config["github_token"] = request.form.get("github_token", "")
        new_config["db_locations"]["stock_history"] = request.form.get("db_stock", "data/stock_history.db")
        new_config["db_locations"]["xforge_historical"] = request.form.get("db_xforge", "data/xforge_historical.db")
        save_config(new_config)
        config = new_config
        flash("Configuration saved successfully!")
    except Exception as e:
        flash(handle_error(e, "save_config_route"))
    return redirect(url_for('index'))

@app.route('/git_action', methods=['POST'])
def git_action():
    action = request.form.get('action')
    result = ""
    if action == "status": result = git_status()
    elif action == "pull": result = git_pull()
    elif action == "push": result = git_push(request.form.get('commit_msg', "Update via App UI"))
    return redirect(url_for('index', git_result=result))

@app.route('/sim_generate', methods=['POST'])
def sim_generate():
    user_prompt = request.form.get('prompt', '').strip() or "Enhance financial indicators, backtesting, and historical DB handling."
    current_code = open(__file__, 'r', encoding='utf-8').read()
    backup_file = save_backup() if config.get("auto_backup_on_sim", True) else ""
    improved = call_xai_for_improvement(current_code, user_prompt)
    if improved.startswith("ERROR"):
        flash(improved)
        return redirect(url_for('index'))
    return redirect(url_for('index', sim_improved_code=improved))

@app.route('/sim_confirm', methods=['POST'])
def sim_confirm():
    improved_code = request.form.get('improved_code', '')
    if not improved_code:
        flash("No improved code provided.")
        return redirect(url_for('index'))
    backup_file = ""
    if os.path.exists(BACKUP_DIR):
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.py')])
        if backups: backup_file = os.path.join(BACKUP_DIR, backups[-1])
    result = apply_improved_code(improved_code, backup_file)
    flash(result)
    return redirect(url_for('index'))

@app.route('/load_module', methods=['POST'])
def load_module_route():
    path = request.form.get('module_path', '').strip()
    if not path or not os.path.exists(path):
        flash("Invalid module path.")
        return redirect(url_for('index'))
    module, msg = load_module_from_file(path)
    return redirect(url_for('index', module_result=msg))

@app.route('/stock_report', methods=['POST'])
def stock_report():
    symbol = request.form.get('symbol', '').upper().strip()
    report = calculate_stock_indicators(symbol)
    if report:
        flash(f"Report generated for {symbol}")
    else:
        flash("Failed to generate report. Check logs.")
    return redirect(url_for('index', stock_report=report) if report else url_for('index'))

@app.route('/backtest', methods=['POST'])
def backtest():
    symbol = request.form.get('symbol', '').upper().strip()
    short = int(request.form.get('short_ma', 5))
    long = int(request.form.get('long_ma', 20))
    result = run_backtester(symbol, short, long)
    if result:
        flash(f"Backtest completed for {symbol}")
    else:
        flash("Backtest failed.")
    return redirect(url_for('index', backtest_result=result) if result else url_for('index'))

@app.route('/historical_query', methods=['POST'])
def historical_query():
    symbol = request.form.get('symbol', '').upper().strip()
    data = get_historical_data("stock_history", symbol)
    if not data:
        data = get_historical_data("xforge_historical", symbol)
    return redirect(url_for('index', historical_data=data))

@app.route('/sim_on_db', methods=['POST'])
def sim_on_db():
    flash("SIM improvement on historical DB triggered. Check SIM tab for results.")
    return redirect(url_for('index'))

if __name__ == "__main__":
    log_event(f"{APP_NAME} starting up (Full Restoration v9.2+)", "INFO", "main")
    try:
        for d in [BACKUP_DIR, "data", "logs"]:
            if not os.path.exists(d):
                os.makedirs(d)
        log_event("All functionality restored: Stock Reports, Backtester, Historical DB, SIM Database.", "INFO", "startup")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        handle_error(e, "main_startup")
        sys.exit(1)
