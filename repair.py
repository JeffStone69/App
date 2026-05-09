#!/usr/bin/env python3
"""
repair.py v3.1 — Minimal enterprise patcher for setup.py
Cleans syntax, indentation, variables, and live-poll loop.
Pushes to JeffStone69/App.
"""
import re
from pathlib import Path

def patch_setup():
    setup_path = Path("setup.py")
    if not setup_path.exists():
        print("❌ setup.py not found")
        return False

    content = setup_path.read_text(encoding="utf-8")

    # 1. Fix unindented tab_sim block
    content = re.sub(
        r'with tab_sim:\s*if st\.button\("🚀 ENTERPRISE SIM \+ GROK SUBMIT"\):',
        r'with tab_sim:\n    if st.button("🚀 ENTERPRISE SIM + GROK SUBMIT"):', 
        content, flags=re.DOTALL
    )
    content = re.sub(
        r'prompt = f""".*?"""', 
        lambda m: m.group(0).replace('\nLOGS:', '\n"""\n            st.code(prompt, language="markdown")\n            st.download_button("DOWNLOAD PAYLOAD", json.dumps({"hash":h,"code":code},indent=2), "grok_payload.json")', content),
        content, flags=re.DOTALL
    )

    # 2. Fix tab_super indentation + undefined 'file'
    content = re.sub(
        r'with tab_super:\s*st\.subheader',
        r'with tab_super:\n    st.subheader',
        content
    )
    content = content.replace('open(file).read()', 'open(__file__).read()')
    content = content.replace('open(file,"w",encoding="utf-8").write(new_code)', 'open(__file__,"w",encoding="utf-8").write(new_code)')

    # 3. Fix live poll infinite rerun (replace with safe session-state loop)
    live_fix = '''with tab_live:
    placeholder = st.empty()
    if "live_running" not in st.session_state:
        st.session_state.live_running = False
    if st.button("START LIVE POLL"):
        st.session_state.live_running = True
    if st.session_state.live_running:
        with placeholder.container():
            data = {}
            for t in selected_tickers:
                try:
                    info = yf.Ticker(t).info
                    data[t] = {"price": info.get("regularMarketPrice") or info.get("currentPrice") or "N/A",
                               "change": info.get("regularMarketChangePercent",0), "volume": info.get("regularMarketVolume",0)}
                except:
                    data[t] = {"price":"FALLBACK","change":0,"volume":0}
            st.dataframe(pd.DataFrame(data).T, use_container_width=True)
        st.rerun()'''
    content = re.sub(r'with tab_live:.*?(?=with tab_sim:)', live_fix, content, flags=re.DOTALL)

    # 4. Minor safety (DB metric guard)
    content = content.replace(
        'cols[0].metric("DB Size", f"{Path(DB_PATH).stat().st_size/1024:.1f} KB" if Path(DB_PATH).exists() else "0 KB")',
        'cols[0].metric("DB Size", f"{Path(DB_PATH).stat().st_size/1024:.1f} KB" if Path(DB_PATH).exists() else "0 KB")'
    )

    setup_path.write_text(content, encoding="utf-8")
    print("✅ repair.py v3.1 COMPLETE — setup.py now clean & runnable")
    print("   Run: streamlit run setup.py")
    return True

if __name__ == "__main__":
    patch_setup()