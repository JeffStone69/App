#!/bin/bash
echo "=== XForge Trader v9.2 Installer ==="
mkdir -p data logs modules
pip install pandas numpy yfinance matplotlib gradio --quiet
echo "✅ All dependencies installed. Run ./launch.command to start"
