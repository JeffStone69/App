#!/usr/bin/env python3
"""
Unified App Script - Cleanup & Enhancement of JeffStone69/App
Combines common parts from SIM.py, shipping.py, xforge_historical_db.py and related files:
- Robust logging & error handling
- Config management (credentials, DB locations)
- SQLite DB utilities
- Self-Improving Module (SIM) using xAI/Grok API
- GitHub push/pull sync
- Web-based UI for user interaction & module loading

Run with: python app.py
Access at: http://localhost:5000

Requires: flask, openai (pip install flask openai)
"""

import os
import sys
import json
import logging
import traceback
import sqlite3
import subprocess
import importlib.util
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, flash
from openai import OpenAI  # xAI-compatible via base_url

# ============== CONFIG & GLOBALS ==============
APP_NAME = "XForge App"
LOG_FILE = "xforge_errors.log"
CONFIG_FILE = "config.json"
BACKUP_DIR = "backups"
DEFAULT_MODEL = "grok-4"  # or "grok-4.3" / latest available

app = Flask(__name__)
app.secret_key = os.urandom(24)  # for flash messages

# ============== ROBUST LOGGING ==============
def setup_logging():
    """Setup robust logging: file + console, with rotation-friendly handler."""
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)
    
    # File handler (append, with timestamp)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

def log_event(message: str, level: str = "INFO", context: str = ""):
    """Centralized event logging with context."""
    full_msg = f"[{context}] {message}" if context else message
    if level.upper() == "DEBUG":
        logger.debug(full_msg)
    elif level.upper() == "WARNING":
        logger.warning(full_msg)
    elif level.upper() == "ERROR":
        logger.error(full_msg)
    else:
        logger.info(full_msg)

def handle_error(e: Exception, context: str = "General") -> str:
    """Robust error handler: logs full traceback and returns user-friendly message."""
    tb = traceback.format_exc()
    log_event(f"ERROR in {context}: {str(e)}\n{tb}", "ERROR", context)
    return f"Error in {context}: {str(e)}. Check {LOG_FILE} for details."

# ============== CONFIG MANAGEMENT ==============
def load_config() -> dict:
    """Load persistent config (credentials, DB paths, etc.)."""
    defaults = {
        "xai_api_key": "",
        "github_token": "",  # Optional for advanced Git ops
        "db_locations": {
            "stock_history": "stock_history.db",
            "xforge_historical": "xforge_historical.db"
        },
        "log_level": "INFO",
        "auto_backup_on_sim": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Merge defaults for new fields
            for key, val in defaults.items():
                if key not in config:
                    config[key] = val
            return config
        except Exception as e:
            handle_error(e, "load_config")
            return defaults
    return defaults

def save_config(config: dict):
    """Save config to disk."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        log_event("Config saved successfully.", "INFO", "save_config")
    except Exception as e:
        handle_error(e, "save_config")

config = load_config()

# ============== DB UTILITIES (Common from repo DB scripts) ==============
def get_db_connection(db_key: str) -> sqlite3.Connection:
    """Get connection to specified DB with error handling."""
    try:
        db_path = config["db_locations"].get(db_key, f"{db_key}.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        log_event(f"Connected to DB: {db_path}", "DEBUG", "get_db_connection")
        return conn
    except Exception as e:
        raise Exception(handle_error(e, f"get_db_connection({db_key})"))

def execute_query(db_key: str, query: str, params: tuple = ()) -> list:
    """Safe query execution with logging."""
    try:
        conn = get_db_connection(db_key)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.commit()
        conn.close()
        log_event(f"Query executed on {db_key}: {query[:100]}...", "DEBUG", "execute_query")
        return results
    except Exception as e:
        handle_error(e, f"execute_query({db_key})")
        return []

# ============== GIT SYNC (Common Git operations) ==============
def git_command(cmd: list, context: str = "git") -> str:
    """Run git command with robust error handling."""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        log_event(f"Git command successful: {' '.join(cmd)}", "INFO", context)
        return result.stdout.strip() or "Success"
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        handle_error(e, f"git_command: {context}")
        return f"Failed: {err_msg}"
    except Exception as e:
        return handle_error(e, f"git_command: {context}")

def git_status() -> str:
    return git_command(["git", "status"], "git_status")

def git_pull() -> str:
    return git_command(["git", "pull"], "git_pull")

def git_push(commit_msg: str = "Auto-update via App UI") -> str:
    try:
        git_command(["git", "add", "."], "git_push_add")
        git_command(["git", "commit", "-m", commit_msg], "git_push_commit")
        return git_command(["git", "push"], "git_push")
    except Exception as e:
        return handle_error(e, "git_push")

# ============== SELF-IMPROVING MODULE (SIM) ==============
def save_backup() -> str:
    """Save current script as timestamped backup."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

def call_xai_for_improvement(current_code: str, user_prompt: str) -> str:
    """Query xAI/Grok to improve the code. Returns improved code or error."""
    if not config["xai_api_key"]:
        return "ERROR: xAI API key not set in Configuration tab."
    
    try:
        client = OpenAI(
            api_key=config["xai_api_key"],
            base_url="https://api.x.ai/v1"  # xAI OpenAI-compatible endpoint
        )
        
        system_prompt = (
            "You are an expert Python developer specializing in robust, self-improving applications. "
            "Analyze the provided script and improve it according to the user's request. "
            "Focus on: better error handling, logging, modularity, performance, security, and new features. "
            "Output ONLY the complete, runnable Python code. No explanations, no markdown fences."
        )
        
        full_user_prompt = (
            f"Current script code:\n\n```python\n{current_code}\n```\n\n"
            f"Improvement request: {user_prompt}\n\n"
            "Return the FULL improved script (keep all existing functionality and add improvements)."
        )
        
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_prompt}
            ],
            max_tokens=12000,
            temperature=0.6
        )
        
        improved_code = response.choices[0].message.content.strip()
        
        # Clean any accidental markdown
        if improved_code.startswith("```python"):
            improved_code = improved_code[9:]
        if improved_code.endswith("```"):
            improved_code = improved_code[:-3]
        
        log_event("xAI improvement generated successfully.", "INFO", "SIM_xai")
        return improved_code.strip()
        
    except Exception as e:
        return handle_error(e, "SIM_xai_call")

def apply_improved_code(improved_code: str, backup_file: str) -> str:
    """Save improved code to current script file (for next launch)."""
    try:
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(improved_code)
        log_event(f"New improved code saved. Backup: {backup_file}. Restart app to load.", "INFO", "SIM_apply")
        return "SUCCESS: Code updated. Please restart the application to load the new version."
    except Exception as e:
        return handle_error(e, "SIM_apply")

# ============== MODULE LOADER ==============
def load_module_from_file(filepath: str):
    """Dynamically load a .py module (for combining common parts)."""
    try:
        spec = importlib.util.spec_from_file_location("dynamic_module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        log_event(f"Module loaded: {filepath}", "INFO", "module_loader")
        return module, f"Module '{os.path.basename(filepath)}' loaded successfully."
    except Exception as e:
        return None, handle_error(e, f"load_module({filepath})")

# ============== FLASK WEB UI (Module-Loading Webpage) ==============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ app_name }} - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: system-ui, sans-serif; }
        .tab { transition: all 0.2s; }
        .log-text { font-family: ui-monospace, monospace; white-space: pre-wrap; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100">
    <div class="max-w-7xl mx-auto p-6">
        <!-- Header -->
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-4xl font-bold text-emerald-400">{{ app_name }}</h1>
                <p class="text-gray-400">Unified Self-Improving Module System • Cleaned & Enhanced</p>
            </div>
            <div class="text-right text-sm">
                <div>Status: <span class="text-emerald-400">Running</span></div>
                <div class="text-gray-500">{{ current_time }}</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="flex border-b border-gray-700 mb-6">
            <button onclick="showTab('dashboard')" class="tab px-6 py-3 font-medium border-b-2 border-emerald-400 text-emerald-400">Dashboard</button>
            <button onclick="showTab('config')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Configuration</button>
            <button onclick="showTab('git')" class="tab px-6 py-3 font-medium hover:text-emerald-400">GitHub Sync</button>
            <button onclick="showTab('sim')" class="tab px-6 py-3 font-medium hover:text-emerald-400">SIM (Self-Improve)</button>
            <button onclick="showTab('modules')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Module Loader</button>
            <button onclick="showTab('logs')" class="tab px-6 py-3 font-medium hover:text-emerald-400">Logs</button>
        </div>

        <!-- DASHBOARD TAB -->
        <div id="dashboard" class="tab-content">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-gray-800 p-6 rounded-xl">
                    <h3 class="font-semibold mb-4">Quick Stats</h3>
                    <div class="space-y-3 text-sm">
                        <div>DBs Connected: <span class="font-mono">{{ db_count }}</span></div>
                        <div>Backups Available: <span class="font-mono">{{ backup_count }}</span></div>
                        <div>Log Size: <span class="font-mono">{{ log_size }} KB</span></div>
                    </div>
                </div>
                <div class="bg-gray-800 p-6 rounded-xl md:col-span-2">
                    <h3 class="font-semibold mb-4">Recent Activity</h3>
                    <div class="log-text text-xs bg-gray-950 p-4 rounded h-32 overflow-auto">{{ recent_logs }}</div>
                </div>
            </div>
        </div>

        <!-- CONFIG TAB -->
        <div id="config" class="tab-content hidden">
            <form method="POST" action="/save_config" class="bg-gray-800 p-8 rounded-2xl space-y-6">
                <h2 class="text-2xl font-semibold">Configuration</h2>
                
                <div>
                    <label class="block text-sm mb-1">xAI API Key (required for SIM)</label>
                    <input type="password" name="xai_api_key" value="{{ config.xai_api_key }}" class="w-full bg-gray-700 p-3 rounded">
                </div>
                
                <div>
                    <label class="block text-sm mb-1">GitHub Token (optional for advanced ops)</label>
                    <input type="password" name="github_token" value="{{ config.github_token }}" class="w-full bg-gray-700 p-3 rounded">
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm mb-1">Stock History DB Path</label>
                        <input type="text" name="db_stock" value="{{ config.db_locations.stock_history }}" class="w-full bg-gray-700 p-3 rounded">
                    </div>
                    <div>
                        <label class="block text-sm mb-1">XForge Historical DB Path</label>
                        <input type="text" name="db_xforge" value="{{ config.db_locations.xforge_historical }}" class="w-full bg-gray-700 p-3 rounded">
                    </div>
                </div>
                
                <button type="submit" class="bg-emerald-500 hover:bg-emerald-600 px-8 py-3 rounded-xl font-medium">Save Configuration</button>
            </form>
        </div>

        <!-- GIT TAB -->
        <div id="git" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl space-y-6">
                <h2 class="text-2xl font-semibold">GitHub Push / Pull Sync</h2>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <form method="POST" action="/git_action">
                        <input type="hidden" name="action" value="status">
                        <button class="w-full bg-gray-700 hover:bg-gray-600 py-3 rounded-xl">Check Status</button>
                    </form>
                    <form method="POST" action="/git_action">
                        <input type="hidden" name="action" value="pull">
                        <button class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-xl">Git Pull</button>
                    </form>
                    <form method="POST" action="/git_action">
                        <input type="hidden" name="action" value="push">
                        <input type="text" name="commit_msg" placeholder="Commit message" class="w-full mb-2 bg-gray-700 p-3 rounded">
                        <button class="w-full bg-emerald-600 hover:bg-emerald-700 py-3 rounded-xl">Git Push</button>
                    </form>
                </div>
                
                {% if git_result %}
                <div class="bg-gray-950 p-4 rounded font-mono text-sm">{{ git_result }}</div>
                {% endif %}
            </div>
        </div>

        <!-- SIM TAB -->
        <div id="sim" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-4">Self-Improving Module (SIM)</h2>
                <p class="text-gray-400 mb-6">Saves current script → Asks Grok xAI to improve it → Saves for next launch upon your confirmation.</p>
                
                <form method="POST" action="/sim_generate" class="space-y-4">
                    <div>
                        <label class="block text-sm mb-1">Improvement Prompt (optional - leave blank for default)</label>
                        <textarea name="prompt" rows="3" class="w-full bg-gray-700 p-4 rounded" placeholder="e.g. Add better async support, improve DB queries, add more error recovery..."></textarea>
                    </div>
                    <button type="submit" class="bg-purple-600 hover:bg-purple-700 px-8 py-3 rounded-xl font-medium">Generate Improved Version with xAI</button>
                </form>
                
                {% if sim_improved_code %}
                <div class="mt-8">
                    <h3 class="font-semibold mb-2">Improved Code (Review Carefully)</h3>
                    <form method="POST" action="/sim_confirm">
                        <textarea name="improved_code" rows="20" class="w-full bg-gray-950 p-4 font-mono text-xs rounded">{{ sim_improved_code }}</textarea>
                        <div class="flex gap-4 mt-4">
                            <button type="submit" class="flex-1 bg-emerald-600 hover:bg-emerald-700 py-3 rounded-xl font-medium">CONFIRM & SAVE FOR NEXT LAUNCH</button>
                            <a href="/" class="flex-1 text-center bg-gray-700 hover:bg-gray-600 py-3 rounded-xl font-medium">Cancel</a>
                        </div>
                    </form>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- MODULE LOADER TAB -->
        <div id="modules" class="tab-content hidden">
            <div class="bg-gray-800 p-8 rounded-2xl">
                <h2 class="text-2xl font-semibold mb-4">Dynamic Module Loader</h2>
                <p class="mb-4 text-gray-400">Load additional .py files to combine common parts dynamically.</p>
                
                <form method="POST" action="/load_module" class="flex gap-4">
                    <input type="text" name="module_path" placeholder="/path/to/another_script.py" class="flex-1 bg-gray-700 p-3 rounded">
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 px-8 rounded-xl">Load Module</button>
                </form>
                
                {% if module_result %}
                <div class="mt-4 p-4 bg-gray-950 rounded">{{ module_result }}</div>
                {% endif %}
            </div>
        </div>

        <!-- LOGS TAB -->
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
        // Show dashboard by default
        document.getElementById('dashboard').classList.remove('hidden');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    try:
        # Gather stats
        db_count = len(config["db_locations"])
        backup_count = len([f for f in os.listdir(BACKUP_DIR) if f.endswith('.py')]) if os.path.exists(BACKUP_DIR) else 0
        log_size = round(os.path.getsize(LOG_FILE) / 1024, 1) if os.path.exists(LOG_FILE) else 0
        
        # Recent logs
        recent_logs = ""
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-15:]
                recent_logs = ''.join(lines)
        
        full_logs = ""
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                full_logs = ''.join(f.readlines()[-100:])
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return render_template_string(
            HTML_TEMPLATE,
            app_name=APP_NAME,
            current_time=current_time,
            config=config,
            db_count=db_count,
            backup_count=backup_count,
            log_size=log_size,
            recent_logs=recent_logs,
            full_logs=full_logs,
            git_result=request.args.get('git_result', ''),
            sim_improved_code=request.args.get('sim_improved_code', ''),
            module_result=request.args.get('module_result', '')
        )
    except Exception as e:
        flash(handle_error(e, "index"))
        return redirect(url_for('index'))

@app.route('/save_config', methods=['POST'])
def save_config_route():
    try:
        new_config = config.copy()
        new_config["xai_api_key"] = request.form.get("xai_api_key", "")
        new_config["github_token"] = request.form.get("github_token", "")
        new_config["db_locations"]["stock_history"] = request.form.get("db_stock", "stock_history.db")
        new_config["db_locations"]["xforge_historical"] = request.form.get("db_xforge", "xforge_historical.db")
        
        save_config(new_config)
        global config
        config = new_config
        flash("Configuration saved successfully!")
    except Exception as e:
        flash(handle_error(e, "save_config_route"))
    return redirect(url_for('index'))

@app.route('/git_action', methods=['POST'])
def git_action():
    action = request.form.get('action')
    result = ""
    if action == "status":
        result = git_status()
    elif action == "pull":
        result = git_pull()
    elif action == "push":
        commit_msg = request.form.get('commit_msg', "Update via App UI")
        result = git_push(commit_msg)
    
    return redirect(url_for('index', git_result=result))

@app.route('/sim_generate', methods=['POST'])
def sim_generate():
    user_prompt = request.form.get('prompt', '').strip()
    if not user_prompt:
        user_prompt = "Make the script more robust, improve error handling, add better logging, enhance the SIM module, and optimize performance. Keep all existing functionality intact."
    
    current_code = ""
    with open(__file__, 'r', encoding='utf-8') as f:
        current_code = f.read()
    
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
    
    # Get latest backup
    backup_file = ""
    if os.path.exists(BACKUP_DIR):
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.py')])
        if backups:
            backup_file = os.path.join(BACKUP_DIR, backups[-1])
    
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

# ============== MAIN ==============
if __name__ == "__main__":
    log_event(f"{APP_NAME} starting up...", "INFO", "main")
    try:
        # Ensure backup dir
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Initial log
        log_event("Application initialized with robust logging and error handling.", "INFO", "startup")
        
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        handle_error(e, "main_startup")
        sys.exit(1)
