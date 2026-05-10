#!/usr/bin/env python3
"""
XFORGE v3.2 — Full .app Bundle Creator
"""

import os
import shutil
import subprocess
from pathlib import Path

print("🚀 Building XFORGE.app with Animated Splash...")

# Clean previous build
shutil.rmtree("dist", ignore_errors=True)
shutil.rmtree("build", ignore_errors=True)

app_name = "XFORGE"
bundle_path = f"dist/{app_name}.app"

# Create bundle structure
os.makedirs(f"{bundle_path}/Contents/MacOS", exist_ok=True)
os.makedirs(f"{bundle_path}/Contents/Resources", exist_ok=True)

# Copy logo
if os.path.exists("logo.jpg"):
    shutil.copy("logo.jpg", f"{bundle_path}/Contents/Resources/logo.jpg")
    print("✅ Logo embedded")

# Main executable script with animated splash
main_script = """#!/usr/bin/env python3
import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import time
import subprocess
import os
import threading

def create_animated_splash():
    root = tk.Tk()
    root.title("XFORGE")
    root.configure(bg="#0a0a0a")
    root.overrideredirect(True)
    
    # Center window
    w, h = 900, 600
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{screen_w//2 - w//2}+{screen_h//2 - h//2}")
    
    # Load animated logo (fallback to static if GIF not present)
    logo_path = os.path.join(os.path.dirname(__file__), "../Resources/logo.jpg")
    try:
        img = Image.open(logo_path)
        if getattr(img, "is_animated", False):
            frames = [ImageTk.PhotoImage(frame.copy()) for frame in ImageSequence.Iterator(img)]
        else:
            frames = [ImageTk.PhotoImage(img.resize((700, 500), Image.Resampling.LANCZOS))]
    except:
        frames = []
    
    label = tk.Label(root, bg="#0a0a0a")
    label.pack(expand=True)
    
    tk.Label(root, text="XFORGE", font=("Helvetica", 48, "bold"), fg="#00ffcc", bg="#0a0a0a").pack()
    tk.Label(root, text="FINANCIAL INTELLIGENCE", font=("Helvetica", 18), fg="#888888", bg="#0a0a0a").pack()
    tk.Label(root, text="Deep Learning • Self Improvement", font=("Helvetica", 12), fg="#666666", bg="#0a0a0a").pack(pady=20)
    
    def animate(i=0):
        if frames:
            label.config(image=frames[i % len(frames)])
            root.after(80, animate, i+1)
    
    animate()
    root.after(2800, root.destroy)  # 2.8 seconds splash
    root.mainloop()

# Show splash
create_animated_splash()

# Launch main app
subprocess.Popen(["python3", os.path.join(os.path.dirname(__file__), "../setup.py")])
"""

with open(f"{bundle_path}/Contents/MacOS/XFORGE", "w") as f:
    f.write(main_script)
os.chmod(f"{bundle_path}/Contents/MacOS/XFORGE", 0o755)

# Info.plist
plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.xforge.quant</string>
    <key>CFBundleVersion</key>
    <string>3.2</string>
    <key>CFBundleExecutable</key>
    <string>XFORGE</string>
    <key>CFBundleIconFile</key>
    <string>logo.icns</string>
    <key>LSBackgroundOnly</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>'''

with open(f"{bundle_path}/Contents/Info.plist", "w") as f:
    f.write(plist)

print(f"✅ {app_name}.app created successfully!")
print("Double-click dist/XFORGE.app to launch with animated splash")

# Final instructions
print("\nNext steps:")
print("   open dist")
