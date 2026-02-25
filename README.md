# Growora v0.4 — Mastery Graph + Skill Map + Studio + Offline Pro

Growora is an offline-first personal tutor that turns natural language goals into adaptive learning plans, concept mastery maps, and guided study sessions.

## Offline promise
- Default `GROWORA_NETWORK_MODE=offline`
- No telemetry. No scraping.
- Outbound network restricted to localhost unless explicitly enabled + allowlisted.
- SQLite + local file storage only.

## v0.4 tour (What’s new)
- **Skill Graph + Mastery engine**: auto-concepts, prereq edges, mastery states, evidence events.
- **Next Best Action planner**: mastery-driven daily plan with interleaving + review + explanations.
- **SkillMap UI** (`/skillmap`) + **Mastery UI** (`/mastery`).
- **Microdrills** APIs and concept-linked grading updates mastery.
- **Studio** (`/studio`, `/studio/import`) for drafts, lesson generation, markdown/pdf import.
- **Offline Pro**: PWA manifest + service worker, backup/restore endpoints, job status endpoint.

## Quickstart (Mac/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
cd web && npm install && cd ..
uvicorn app.main:app --reload --port 8000 --app-dir server
# another terminal
cd web && npm run dev
```

## Quickstart (Windows)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r server\requirements.txt
cd web && npm install && cd ..
uvicorn app.main:app --reload --port 8000 --app-dir server
:: another terminal
cd web && npm run dev
```

## SkillMap + Mastery usage
1. Create course
2. `POST /api/graph/rebuild?course_id=...`
3. Open `/skillmap` and `/mastery`
4. Submit evidence via quizzes/flashcards/drills

## Studio usage
- Create draft: `POST /api/studio/course`
- Generate lesson content: `POST /api/studio/lesson/generate`
- Import markdown: `POST /api/studio/import/markdown`
- Import pdf outline: `POST /api/studio/import/pdf_outline`

## PWA install
- App serves `manifest.webmanifest` + `sw.js`
- Install via browser “Install App” prompt once served over localhost

## Backup/Restore
- Create: `POST /api/backup/create`
- Restore: `POST /api/backup/restore`
- Safe default restore creates a new profile (`Restored - YYYY-MM-DD`)

## Optional Ollama
- `GROWORA_LLM_PROVIDER=ollama`
- `GROWORA_OLLAMA_URL=http://localhost:11434`
- `GROWORA_OLLAMA_MODEL=llama3.1`

## Release artifacts
```bash
python scripts/make_release_zip.py
python scripts/make_course_sample.py
python scripts/make_demo_pack.py
```

Outputs:
- `dist/growora-github-ready.zip`
- `dist/sample_course_spec.json`
- `dist/demo_triad369_with_skillgraph.json`
