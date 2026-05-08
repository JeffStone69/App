#!/bin/bash
# XForge Trader v9.2 Beta – Final Robust Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_fullscreen_logo() {
    if [ -f "logo.jpg" ]; then
        qlmanage -p logo.jpg > /dev/null 2>&1 &
        sleep 3
        pkill -f "qlmanage" 2>/dev/null || true
    fi
}

if [ ! -f ".xforge_installed" ]; then
    echo "First run – installing everything..."
    python3 -m pip install -r requirements.txt --quiet
    python3 setup.py install --quiet
    python3 fix_all_modules.py
    touch .xforge_installed
    echo "Setup complete."
else
    show_fullscreen_logo
fi

# Run core modules
[ -f xforge_historical_db.py ] && python3 xforge_historical_db.py &
[ -f SIM.py ] && exec python3 SIM.py
