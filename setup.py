import os
import subprocess
import sys

print("🚀 XForge Trader - Dependency Installer\n")

# Create required folders
folders = ["data", "logs", "backups"]
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"✅ Created folder: {folder}/")

# Install dependencies (in correct order)
print("\n📦 Installing dependencies...")

packages = [
    "flask",
    "pandas",
    "yfinance",
    "openai",
    "ib_insync",
    "eventkit",
    "requests",
    "numpy"
]

try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + packages)
    print("\n✅ All dependencies installed successfully!")
except subprocess.CalledProcessError as e:
    print(f"\n❌ Installation failed: {e}")
    sys.exit(1)

print("\n🎉 Setup complete!")
print("Run the app with: python3 app.py")
print("Then open http://127.0.0.1:5000 in your browser")