#!/bin/bash
cd "$(dirname "$0")"
[ -f logo.jpg ] && qlmanage -p logo.jpg > /dev/null 2>&1 & sleep 2.5 && pkill -f qlmanage 2>/dev/null || true
exec python3 modules/SIM.py
