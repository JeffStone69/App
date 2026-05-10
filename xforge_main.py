#!/usr/bin/env python3
import sys
import subprocess
import tkinter as tk
from PIL import Image, ImageTk
import time
import threading
import os

status_text = "Initializing XFORGE Financial Intelligence..."

def update_status(msg):
    global status_text
    status_text = msg
    if 'status_label' in globals():
        status_label.config(text=status_text)

def fullscreen_splash():
    global status_label
    root = tk.Tk()
    root.title("XFORGE")
    root.configure(bg="#0a0a0a")
    
    # Fullscreen
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    
    # Background logo (centered)
    try:
        logo_path = os.path.join(os.path.dirname(sys.executable), "logo.jpg")
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img = img.resize((900, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(root, image=photo, bg="#0a0a0a")
            logo_label.image = photo
            logo_label.place(relx=0.5, rely=0.4, anchor="center")
    except:
        pass

    # Title
    tk.Label(root, text="XFORGE", font=("Helvetica", 72, "bold"), 
             fg="#00ffcc", bg="#0a0a0a").place(relx=0.5, rely=0.65, anchor="center")
    
    tk.Label(root, text="FINANCIAL INTELLIGENCE", font=("Helvetica", 24), 
             fg="#00ff88", bg="#0a0a0a").place(relx=0.5, rely=0.73, anchor="center")
    
    # Status Updates
    global status_label
    status_label = tk.Label(root, text=status_text, font=("Helvetica", 16), 
                           fg="#888888", bg="#0a0a0a")
    status_label.place(relx=0.5, rely=0.85, anchor="center")

    update_status("Loading modules...")
    time.sleep(0.8)
    update_status("Connecting to market data feeds...")
    time.sleep(0.8)
    update_status("Initializing backtester & live engine...")
    time.sleep(0.8)
    update_status("Launching interfaces...")

    root.after(2800, root.destroy)   # 2.8 seconds total
    root.mainloop()

# === SHOW FULLSCREEN SPLASH ===
fullscreen_splash()

# === LAUNCH MAIN APP (Terminal stays hidden via --windowed) ===
update_status("Starting Gradio + Streamlit...")
if os.path.exists("setup.py"):
    subprocess.Popen(["python3", "setup.py"])
else:
    print("XFORGE Standalone Ready")
