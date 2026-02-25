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


## Classroom Mode (v0.5)
- Create classroom: `/classrooms`
- Start live session: `/classroom/:classroomId/session/:sessionId`
- Whiteboard supports pen/erase/shapes/text, undo/redo, snapshot and PNG export.
- Presenter mode can generate decks from lessons/concepts and push slides.
- Live quizzes and teach-back scoring work offline and update mastery per learner profile.
- Session summary includes attendance, engagement, quiz/teachback outcomes and next steps.

### Running multiple learners on one machine
- Create multiple profiles in `/profiles`.
- Add profile IDs as classroom members.
- Switch active profile from top nav profile selector.

### Offline scoring details
- Teach-back scoring uses local keyword/rubric heuristics when no LLM is configured.
- Live quiz and teach-back mastery updates are profile-specific.

### Screenshot placeholders
- `docs/screenshots/classroom-session.png` (placeholder)
- `docs/screenshots/classroom-summary.png` (placeholder)


## LAN Mode (v0.6)
Growora can host a classroom on your local Wi-Fi so multiple devices can join.

### Safety first
- Default mode is **local only** (`GROWORA_NETWORK_MODE=local`, bind `127.0.0.1`).
- Enable LAN mode explicitly.
- Use private/home Wi-Fi only (avoid public networks).
- Rotate room codes often and stop hosting when done.

### LAN host workflow
1. Facilitator opens `/classrooms`, starts a classroom session.
2. Create LAN room with `/api/lan/rooms/create`.
3. Share join URL/QR: `http://<LAN_IP>:8000/join/<ROOM_CODE>`.
4. Learners join and remain pending until facilitator approves.
5. Approved learners sync via WebSocket in `/ws/lan/{room_code}`.

### LAN scripts
- Unix: `scripts/host_lan_unix.sh`
- Windows: `scripts/host_lan_windows.bat`

### Local-only scripts (existing)
- Unix: `run_unix.sh`
- Windows: `run_windows.bat`

## Offline Sync (v0.7)

Growora supports **encrypted offline sync packages** (`*.growora-sync.zip`) so learning records can move between devices with no cloud.

### What sync export includes
- Profile metadata (name/role only, no secrets)
- Course summaries
- Learning events (append-only)
- Mastery snapshots
- Flashcard review logs
- Optional session/classroom events (`scope=include_sessions`)
- Certificates

### Export / import steps
1. Open `/settings/sync`.
2. Enter profile ID, scope, bounds (days/events), and passphrase.
3. Export package.
4. On target host, import package with same passphrase.
5. Check merge summary + sync audit list.

### Privacy + safety
- No telemetry, no cloud upload.
- Manifest is plain JSON but excludes sensitive learning content.
- Payload is encrypted and integrity-protected.
- Wrong passphrase or tampered payload is rejected.

### LAN mesh sync (optional)
- Host creates one-time pairing code in LAN host page.
- Learner uses pairing code in LAN session page and uploads sync package.
- Pairing code is single-use and expires in 5 minutes.
- Use private/home Wi-Fi only; avoid public networks.

## Selective Sync + Family Sharing (v0.8)

### Selective Sync wizard (`/settings/sync`)
1. Choose profile
2. Choose courses (CSV multi-select)
3. Choose concept filters (SkillMap concept IDs), optionally include prerequisites/dependents
4. Choose data types (`evidence`, `mastery`, `flashcards`, `sessions`, `classroom`, `certificates`)
5. Choose timeframe (`last_days`) + max events
6. Enter passphrase and export encrypted package

Use **Preview** first to verify counts and estimated size before exporting.

### Family sharing (`/family-share`)
- **Course Push**: parent exports one selected course and kid imports it into a chosen target profile.
- **Progress Pull**: kid exports course progress and parent imports it back.
- **Progress-only token policy**: parent can create one-time token secrets (hashed at rest) that allow progress imports for a single course; expired/revoked tokens are rejected.

### Safety defaults
- Offline-only architecture, no cloud/telemetry.
- Selective export minimizes accidental sharing.
- Attachments/chat are excluded by default unless explicitly selected in policy.
- Packages are encrypted and integrity checked before merge.

## Local Marketplace + Course Registry (v0.9)

### Marketplace workflow (`/marketplace`)
1. Add a local folder source containing `*.triad369.zip` / `*.course.zip` packages.
2. Scan source to discover available versions.
3. Install selected package to create/update a registry item.
4. Prepare update to a newer version (creates staged candidate course).
5. Review diff (`/api/registry/diff`) and run merge plan/apply for conflicts.
6. Commit update or rollback to a previous package version.

### Safety promise
- Offline marketplace only (no cloud, no telemetry).
- User lesson edits are tracked and protected through merge planning.
- Updates do not silently overwrite edited lessons.

### Optional LAN catalog
- Host can explicitly enable LAN catalog sharing.
- Approved LAN clients can list/request shared package metadata only with token auth.
