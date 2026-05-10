#!/usr/bin/env python3
import gradio as gr
import yfinance as yf
import subprocess
from datetime import datetime

def run_historical(tickers="AAPL,TSLA,NVDA,SPY"):
    results = []
    for t in [x.strip().upper() for x in tickers.split(",")]:
        try:
            df = yf.download(t, period="1y", progress=False)
            results.append(f"✅ {t}: {len(df)} rows loaded")
        except Exception as e:
            results.append(f"❌ {t}: {e}")
    return "\n".join(results)

def launch_dashboard():
    subprocess.Popen(["streamlit", "run", "live_dashboard.py", "--server.headless=true", "--server.port=8501"])
    return "🌐 Dashboard launched at http://localhost:8501"

with gr.Blocks(title="Elite Quant") as demo:
    gr.Markdown("# 🚀 Elite Quant - FIXED & LIVE")
    with gr.Tabs():
        with gr.Tab("📊 Historical Data"):
            gr.Interface(
                fn=run_historical,
                inputs=gr.Textbox(value="AAPL,TSLA,NVDA,SPY", label="Tickers"),
                outputs=gr.Textbox(label="Result"),
            )
        with gr.Tab("📡 Live Dashboard"):
            output = gr.Textbox(label="Status")
            gr.Button("🚀 Launch Live Dashboard", variant="primary").click(
                launch_dashboard, outputs=output
            )
        with gr.Tab("Status"):
            gr.Markdown(f"**Fixed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
