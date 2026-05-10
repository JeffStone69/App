#!/bin/bash
# =============================================
# XFORGE ELITE QUANT - macOS CLEAN LAUNCHER
# Double-click in Finder → Splash + App
# =============================================

cd "$(dirname "$0")"

# Persistent Splash Screen with your logo
python3 -c '
import tkinter as tk
from PIL import Image, ImageTk
import time
import os

root = tk.Tk()
root.title("XFORGE")
root.configure(bg="#0a0a0a")
root.overrideredirect(True)  # Remove window borders

# Center on screen
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"800x500+{screen_width//2-400}+{screen_height//2-250}")

# Load logo
logo_path = os.path.join(os.path.dirname(__file__), "logo.jpg")
if os.path.exists(logo_path):
    img = Image.open(logo_path)
    img = img.resize((600, 400), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    label = tk.Label(root, image=photo, bg="#0a0a0a")
    label.image = photo
    label.pack(expand=True)

# Text
tk.Label(root, text="XFORGE FINANCIAL INTELLIGENCE", 
         font=("Helvetica", 24, "bold"), fg="#00ffcc", bg="#0a0a0a").pack()
tk.Label(root, text="Deep Learning • Self Improvement", 
         font=("Helvetica", 12), fg="#888888", bg="#0a0a0a").pack(pady=10)

root.update()

# Keep splash for 3 seconds then launch main app
time.sleep(3)
root.destroy()

# Launch the real app
import subprocess
subprocess.Popen(["python3", "setup.py"])
' &

echo "🚀 XFORGE Launched - Check terminal + browser windows"
