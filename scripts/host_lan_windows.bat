@echo off
set GROWORA_NETWORK_MODE=lan
set GROWORA_BIND_HOST=0.0.0.0
set GROWORA_BIND_PORT=8000
echo [Growora LAN Host] Starting on 0.0.0.0:8000
python -m venv .venv
call .venv\Scripts\activate
pip install -r server\requirements.txt
cd web && npm install && cd ..
start cmd /k "call .venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir server"
start cmd /k "cd web && npm run dev"
