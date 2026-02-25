# Growora v0.3 — Tutor Sessions + Multi-Profile + Worksheet Forge

Offline-first personal tutoring platform: build courses, run guided study sessions, generate materials from your own documents, and track progress locally.

## Offline promise
- Default: `GROWORA_NETWORK_MODE=offline`
- No telemetry, no scraping, local-only data
- Offline mode allows localhost only
- Online mode allows only `GROWORA_ALLOWED_HOSTS`

## What’s new in v0.3
- **Multi-profile household mode** (`/profiles`) with active profile switching.
- **Tutor sessions** (`/session/:id`): timer, events, reflection, coach summary.
- **Library → Forge** (`/forge`): generate flashcards/worksheets/quizzes/summaries from uploaded docs.
- **Streak + analytics** endpoints and dashboard widgets.
- **Tutor chat drawer** with deterministic offline fallback and optional Ollama enrichment.
- **Triad369 export upgrade** includes `learning_record.json`.

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

## Key v0.3 APIs
- Profiles: `GET/POST/PATCH /api/profiles`, `POST /api/profiles/{id}/select`
- Sessions: `POST /api/sessions/start|event|end`, `GET /api/sessions/recent`, `GET /api/sessions/{id}`
- Analytics: `GET /api/dashboard/analytics`, `GET /api/streak?course_id=`
- Forge: `POST /api/forge/run`, `GET /api/forge/jobs`, `POST /api/forge/jobs/{id}/apply_to_course`
- Tutor chat: `POST /api/tutor/chat`

## Environment variables
See `.env.example`.

## Release tooling
```bash
python scripts/make_release_zip.py
python scripts/make_course_sample.py
```
Artifacts:
- `dist/growora-github-ready.zip`
- `dist/sample_course_spec.json`

## License
MIT
