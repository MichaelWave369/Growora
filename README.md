# Growora

**Natural language → your personal tutor (offline-first).**

> Tell me what you want to learn. Growora builds an 8-week curriculum with daily practice, quizzes, progress tracking, and SM-2 flashcards — locally.

## Offline promise
- Default mode is `GROWORA_NETWORK_MODE=offline`.
- No telemetry, no scraping, no hidden outbound calls.
- In offline mode, only localhost calls are allowed (e.g., local Ollama).
- Data is stored in local SQLite at `server/data/growora.db`.

## Monorepo layout
- `server/` FastAPI + SQLModel + SQLite
- `web/` React + Vite + TypeScript

## Quickstart (Mac/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
cd web && npm install && cd ..
uvicorn app.main:app --reload --port 8000 --app-dir server
# in another terminal
cd web && npm run dev
```

Or one command:
```bash
./run_unix.sh
```

## Quickstart (Windows)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r server\requirements.txt
cd web && npm install && cd ..
uvicorn app.main:app --reload --port 8000 --app-dir server
:: in another terminal
cd web && npm run dev
```

Or one-click:
```bat
run_windows.bat
```

## Optional local LLM (Ollama)
1. Install Ollama and run a local model:
   `ollama run llama3.1`
2. Set env:
   - `GROWORA_LLM_PROVIDER=ollama`
   - `GROWORA_OLLAMA_URL=http://localhost:11434`
   - `GROWORA_OLLAMA_MODEL=llama3.1`

If not configured, Growora uses deterministic template generation and still works fully offline.

## Export and optional publish
- Export: `POST /api/export/course/{course_id}` creates a zip in `server/data/exports/`.
- Publish to CoEvo (optional): configure `COEVO_URL` + `COEVO_API_KEY`, then call `POST /api/publish/coevo/{course_id}`.
- Without config, API returns a helpful `400` and stays in export-only mode.

## Environment variables
See `.env.example`.

## License
MIT
