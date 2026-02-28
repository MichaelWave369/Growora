#!/usr/bin/env bash
set -e
export GROWORA_NETWORK_MODE=lan
export GROWORA_BIND_HOST=0.0.0.0
export GROWORA_BIND_PORT=8000
echo "[Growora LAN Host] Starting on 0.0.0.0:8000"
python3 -m venv .venv || true
source .venv/bin/activate
pip install -r server/requirements.txt
(cd web && npm install)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir server &
(cd web && npm run dev)
