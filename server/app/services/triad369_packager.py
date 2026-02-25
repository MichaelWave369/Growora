import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.models import Course, Flashcard, Lesson, StudySession


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_package(course: Course, session: Session) -> Path:
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course.id).order_by(Lesson.order_index, Lesson.id)).all()
    flashcards = session.exec(select(Flashcard).where(Flashcard.course_id == course.id, Flashcard.profile_id == course.profile_id)).all()
    sessions = session.exec(select(StudySession).where(StudySession.course_id == course.id, StudySession.profile_id == course.profile_id)).all()

    out = Path("server/data/exports"); out.mkdir(parents=True, exist_ok=True)
    zpath = out / f"triad369_course_{course.id}.zip"
    manifest = {
        "format": "triad369-course@1",
        "course_id": course.id,
        "title": course.title,
        "topic": course.topic,
        "version": "1.1.0",
        "created_at": datetime.utcnow().isoformat(),
        "author": "local-user",
        "license": "MIT",
        "checksums": {},
    }

    learning_record = {
        "sessions": [
            {
                "id": s.id,
                "lesson_id_optional": s.lesson_id_optional,
                "planned_minutes": s.planned_minutes,
                "actual_minutes": s.actual_minutes,
                "mode": s.mode,
                "notes_md": s.notes_md,
            }
            for s in sessions
        ],
        "streak_history": [1 if s.ended_at else 0 for s in sessions][-30:],
        "mastery_stats": {"estimated_mastery": min(100, 50 + len(sessions) * 2)},
    }

    files = {
        "course.json": json.dumps(course.model_dump(), default=str, indent=2).encode(),
        "certificate_template.html": f"<html><body><h1>{course.title}</h1></body></html>".encode(),
        "README_course.md": b"Import this package via /api/import/triad369",
        "lessons/flashcards.json": json.dumps([f.model_dump() for f in flashcards], default=str, indent=2).encode(),
        "learning_record.json": json.dumps(learning_record, default=str, indent=2).encode(),
    }
    for idx, l in enumerate(lessons, start=1):
        week = ((idx - 1) // max(course.days_per_week, 1)) + 1
        day = ((idx - 1) % max(course.days_per_week, 1)) + 1
        files[f"lessons/week{week:02d}_day{day:02d}.md"] = l.content_md.encode()
        files[f"lessons/quizzes/week{week:02d}_day{day:02d}.quiz.json"] = l.quiz_json.encode()

    for name, data in files.items():
        manifest["checksums"][name] = _sha256(data)

    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, data in files.items():
            zf.writestr(name, data)
    return zpath


def validate_package(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode())
        checksums = manifest.get("checksums", {})
        errors = []
        for name, expected in checksums.items():
            actual = _sha256(zf.read(name))
            if actual != expected:
                errors.append(name)
    return {"ok": not errors, "errors": errors}
