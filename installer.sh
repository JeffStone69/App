#!/bin/bash
echo "=== XForge Trader v9.2 Full Installer ==="
mkdir -p data logs modules
pip install pandas numpy yfinance matplotlib gradio --quiet
echo "✅ Installation complete. Run ./launch.command"
