#!/bin/bash
# XForge Trader v9.2 Beta – Enhanced macOS Launcher
# Displays fullscreen logo, handles first-run install + folder creation,
# then launches main script functions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function: Display fullscreen logo (macOS only)
show_fullscreen_logo() {
    if [ -f "logo.jpg" ]; then
        # Use Quick Look for clean fullscreen image display (auto-closes after ~3s)
        qlmanage -p logo.jpg > /dev/null 2>&1 &
        LOGO_PID=$!
        sleep 3
        kill $LOGO_PID 2>/dev/null || true
        # Alternative fallback (opens in Preview fullscreen)
        # open -a Preview logo.jpg && sleep 2 && osascript -e 'tell application "Preview" to activate' -e 'tell application "System Events" to keystroke "f" using {command down}'
    fi
}

# Function: First-run installation and folder creation
first_run_install() {
    echo "First run detected. Installing dependencies and setting up XForge Trader..."
    
    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        python3 -m pip install -r requirements.txt --quiet
    fi
    
    # Run setup.py if present
    if [ -f "setup.py" ]; then
        python3 setup.py install --quiet
    fi
    
    # Create required folders and files for first use
    mkdir -p "$SCRIPT_DIR/data"
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$SCRIPT_DIR/db_backups"
    
    # Create marker file to indicate installation complete
    touch "$SCRIPT_DIR/.xforge_installed"
    
    # Initialize default database if missing
    if [ ! -f "stock_history.db" ]; then
        python3 -c "
import sqlite3
conn = sqlite3.connect('stock_history.db')
conn.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, price REAL)')
conn.commit()
conn.close()
" 2>/dev/null || true
    fi
    
    echo "Installation complete. Launching application..."
    sleep 1
}

# Main logic
if [ ! -f ".xforge_installed" ]; then
    # First use: install + create everything
    first_run_install
else
    # Subsequent launch: show logo
    show_fullscreen_logo
fi

# Execute initial script calls (common to all runs)
if [ -f "xforge_historical_db.py" ]; then
    python3 xforge_historical_db.py > /dev/null 2>&1 &
fi

# Launch main application functions (SIM.py is the primary script)
if [ -f "SIM.py" ]; then
    python3 SIM.py
else
    echo "Error: SIM.py not found. Please ensure all files are present."
    exit 1
fi
