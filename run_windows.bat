@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -r server\requirements.txt
cd web && npm install && cd ..
start cmd /k "call .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000 --app-dir server"
start cmd /k "cd web && npm run dev"
