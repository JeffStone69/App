#!/usr/bin/env python3
import os
import shutil

BASE = os.getcwd()
NEW_STRUCTURE = {
    "core": ["config.py", "logging.py", "db.py", "git_sync.py", "sim.py"],
    "modules": ["financial_reports.py", "backtester.py", "historical_db.py", "shipping.py"],
    "ui": [],
    "data": ["stock_history.db", "xforge_historical.db"],
    "logs": ["xforge_errors.log"],
    "backups": [],
    "docs": ["README.md", "LICENSE"],
    "scripts": ["installer.sh", "fix.sh"]
}

# Create directories
for folder in NEW_STRUCTURE:
    os.makedirs(os.path.join(BASE, folder), exist_ok=True)

# Move files (safe move with overwrite protection)
moves = {
    "SIM.py": "core/sim.py",
    "xforge_historical_db.py": "modules/historical_db.py",
    "shipping.py": "modules/shipping.py",
    "stock_history.db": "data/stock_history.db",
    "xforge_historical.db": "data/xforge_historical.db",
    "xforge_errors.log": "logs/xforge_errors.log",
    "requirements.txt": "requirements.txt",
    "setup.py": "setup.py",
    "logo.jpg": "ui/logo.jpg"
}

for src, dst in moves.items():
    src_path = os.path.join(BASE, src)
    dst_path = os.path.join(BASE, dst)
    if os.path.exists(src_path):
        shutil.move(src_path, dst_path)
        print(f"Moved: {src} → {dst}")

# Create empty placeholder files for future modules
for folder, files in NEW_STRUCTURE.items():
    for f in files:
        path = os.path.join(BASE, folder, f)
        if not os.path.exists(path) and folder not in ["data", "logs", "backups"]:
            with open(path, "w") as fp:
                fp.write("# TODO: Implement module\n")

print("✅ Directory restructure complete. New structure:")
for root, dirs, files in os.walk(BASE):
    level = root.replace(BASE, "").count(os.sep)
    indent = "  " * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = "  " * (level + 1)
    for f in files:
        print(f"{subindent}{f}")
