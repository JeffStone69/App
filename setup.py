import os
import subprocess
import sys

print("🚀 Installing all required packages for XForge Trader...\n")

# Install dependencies
packages = ["flask", "pandas", "yfinance", "openai", "ib_insync", "eventkit", "requests", "numpy"]

try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    for pkg in packages:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", pkg])
    print("\n✅ All packages installed successfully!")
except Exception as e:
    print(f"❌ Error during install: {e}")
    sys.exit(1)

print("\n🎉 Setup done! Now run: python3 app.py")