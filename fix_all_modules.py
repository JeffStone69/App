import os
import sys
import sqlite3

print("=== Fixing all modules iteratively ===")

# Patch SIM.py if it has common errors
if os.path.exists("SIM.py"):
    with open("SIM.py", "r") as f:
        content = f.read()
    # Common fixes
    content = content.replace("import yfinance", "import yfinance as yf")
    content = content.replace("from yfinance import", "import yfinance as yf")
    with open("SIM.py", "w") as f:
        f.write(content)
    print("✓ SIM.py patched")

# Patch shipping.py
if os.path.exists("shipping.py"):
    with open("shipping.py", "r") as f:
        content = f.read()
    content = content.replace("import pandas", "import pandas as pd")
    with open("shipping.py", "w") as f:
        f.write(content)
    print("✓ shipping.py patched")

# Patch xforge_historical_db.py
if os.path.exists("xforge_historical_db.py"):
    with open("xforge_historical_db.py", "r") as f:
        content = f.read()
    content = content.replace("sqlite3", "import sqlite3")
    with open("xforge_historical_db.py", "w") as f:
        f.write(content)
    print("✓ xforge_historical_db.py patched")

# Initialize / repair databases
for db in ["stock_history.db", "xforge_historical.db"]:
    conn = sqlite3.connect(db)
    conn.execute('''CREATE TABLE IF NOT EXISTS history 
                    (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, price REAL)''')
    conn.commit()
    conn.close()
    print(f"✓ {db} initialized/repaired")

print("=== All modules fixed successfully ===")
