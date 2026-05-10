#!/usr/bin/env python3
"""
XFORGE v4.1 — Fixed PyInstaller Standalone (Zero Dependencies)
"""

import os
import subprocess
import shutil

print("🚀 Building Standalone XFORGE (Fixed PyInstaller)...")

# Install PyInstaller + Pillow
subprocess.run(["pip", "install", "pyinstaller", "pillow"], check=True)

# Clean old builds
shutil.rmtree("dist", ignore_errors=True)
shutil.rmtree("build", ignore_errors=True)

# Single entry point
with open("xforge_main.py", "w") as f:
    f.write('''#!/usr/bin/env python3
import sys
import subprocess
import tkinter as tk
from PIL import Image, ImageTk
import time
import os

def show_splash():
    root = tk.Tk()
    root.title("XFORGE")
    root.configure(bg="#0a0a0a")
    root.overrideredirect(True)
    
    w, h = 900, 600
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{sw//2 - w//2}+{sh//2 - h//2}")
    
    # Logo
    try:
        logo_path = os.path.join(os.path.dirname(sys.executable), "logo.jpg")
        if os.path.exists(logo_path):
            img = Image.open(logo_path).resize((700, 480), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            tk.Label(root, image=photo, bg="#0a0a0a").pack(expand=True)
    except:
        pass
    
    tk.Label(root, text="XFORGE", font=("Helvetica", 48, "bold"), fg="#00ffcc", bg="#0a0a0a").pack()
    tk.Label(root, text="FINANCIAL INTELLIGENCE", font=("Helvetica", 18), fg="#00ff88", bg="#0a0a0a").pack()
    tk.Label(root, text="Deep Learning • Self Improvement", font=("Helvetica", 12), fg="#666666", bg="#0a0a0a").pack(pady=10)
    
    root.update()
    time.sleep(2.8)
    root.destroy()

show_splash()

# Launch main application
if os.path.exists("setup.py"):
    subprocess.Popen(["python3", "setup.py"])
else:
    print("✅ XFORGE Standalone Ready")
''')

# FIXED PyInstaller Command
cmd = [
    "pyinstaller",
    "--name", "XFORGE",
    "--onedir",           # Fixed: was --onefolder
    "--windowed",
    "--add-data", "logo.jpg:.",
    "--add-data", "setup.py:.",
    "--add-data", "live_dashboard.py:.",
    "--hidden-import", "gradio",
    "--hidden-import", "streamlit",
    "--hidden-import", "ib_insync",
    "--hidden-import", "plotly.express",
    "--hidden-import", "yfinance",
    "--hidden-import", "sqlalchemy",
    "--collect-all", "gradio",
    "--collect-all", "streamlit",
    "xforge_main.py"
]

print("Building executable (this may take 60-90 seconds)...")
subprocess.run(cmd, check=True)

print("\n🎉 BUILD SUCCESSFUL!")
print("Launch with: dist/XFORGE/XFORGE")
print("You can distribute the whole 'dist/XFORGE' folder")
