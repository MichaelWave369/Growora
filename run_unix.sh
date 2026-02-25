#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
(cd web && npm install)
uvicorn app.main:app --reload --port 8000 --app-dir server &
(cd web && npm run dev)
