# Growora v0.9.1-rc1 Release Notes

## Highlights
- Offline-first FastAPI + React release candidate with selective sync, family-share, registry/marketplace and LAN classroom flows.
- CI now supports deterministic web dependency installation via `web/package-lock.json`.
- Frontend build stability fixes for async React effects and kiosk fullscreen interaction.
- Release packaging script hardened to skip transient build/cache artifacts.

## Quick Start
- Unix:
  - `pip install -r server/requirements.txt`
  - `cd web && npm ci && cd ..`
  - `uvicorn app.main:app --reload --port 8000 --app-dir server`
  - In a second terminal: `cd web && npm run dev`
- Windows:
  - `pip install -r server\requirements.txt`
  - `cd web && npm ci && cd ..`
  - `uvicorn app.main:app --reload --port 8000 --app-dir server`
  - In a second terminal: `cd web && npm run dev`

## Safety Promise
- No telemetry, no scraping, no cloud requirement.
- Local-first defaults (`localhost`, SQLite/file storage).
- LAN features remain explicit opt-in and should be used only on trusted networks.

## Known Limits
- Ollama/LLM integration remains optional; when not configured, tutor uses offline fallback behavior.
- This release does not include remote cloud sync by design.

## Release Checklist
- `python -m compileall server/app`
- `PYTHONPATH=server pytest -q`
- `cd web && npm run build`
- `python scripts/make_release_zip.py`
