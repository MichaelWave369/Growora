# Growora v0.2 — Super Tutor

**Natural language → your personal tutor (offline-first).**

Growora builds an 8-week course with daily exercises, quizzes, SM-2 flashcards, adaptive planning, and a local knowledge library (PDF/MD/TXT).

## Offline promise
- Default mode: `GROWORA_NETWORK_MODE=offline`
- No telemetry, no scraping, no hidden outbound calls
- Offline mode allows localhost only
- Online mode allows only `GROWORA_ALLOWED_HOSTS`
- SQLite local DB: `server/data/growora.db`

## New in v0.2
- **Knowledge Library**: upload/search/tag/delete documents at `/library`
- **Adaptive planner**: smarter `/today` + next 7-day preview
- **Course editor**: `/course/:id/edit` title/schedule/difficulty/reorder/regen week
- **Triad369 package**: export/import/validate course zips
- **Safer CoEvo publish**: test connection + dry-run + publish logs
- **Certificate verify**: `/verify/:cert_id`
- **Release tooling**: scripts for github-ready zip and sample course spec

## Monorepo
- `server/` FastAPI + SQLModel + SQLite
- `web/` React + Vite + TypeScript

## Quickstart (Mac/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
cd web && npm install && cd ..
uvicorn app.main:app --reload --port 8000 --app-dir server
# new terminal
cd web && npm run dev
```

## Quickstart (Windows)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r server\requirements.txt
cd web && npm install && cd ..
uvicorn app.main:app --reload --port 8000 --app-dir server
:: new terminal
cd web && npm run dev
```

## Optional Ollama (local LLM)
- `GROWORA_LLM_PROVIDER=ollama`
- `GROWORA_OLLAMA_URL=http://localhost:11434`
- `GROWORA_OLLAMA_MODEL=llama3.1`

If not set, deterministic template generation is used.

## Library (attachments + search)
- Upload: `POST /api/library/upload` (multipart)
- Search: `GET /api/library/search?q=...`
- Stored files: `server/data/uploads/`
- Extracted text cache: `server/data/extracted/`

## Adaptive planner
- `GET /api/courses/{id}/plan/today`
- `GET /api/courses/{id}/plan/next7`
- Uses completion + quiz signals + missed-day rollover

## Triad369 export/import
- Export: `POST /api/export/triad369/{course_id}`
- Import: `POST /api/import/triad369`
- Validate: `POST /api/export/triad369/validate`

## Safe CoEvo publish (optional opt-in)
- Configure `COEVO_URL` + `COEVO_API_KEY`
- Test connection: `GET /api/publish/test`
- Dry run publish: `POST /api/publish/coevo/{id}?dry_run=1`
- Real publish: `POST /api/publish/coevo/{id}?dry_run=0`
- Logs: `GET /api/publish/logs`

## Release tooling
```bash
python scripts/make_release_zip.py
python scripts/make_course_sample.py
```
Outputs:
- `dist/growora-github-ready.zip`
- `dist/sample_course_spec.json`

## License
MIT
