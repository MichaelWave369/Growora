import io
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.db import get_session
from app.models import Certificate, Course, Flashcard, Lesson, Task, Week
from app.services.course_gen import CourseSpec, generate_course_payload, parse_intake

router = APIRouter(prefix="/api", tags=["courses"])


class IntakeRequest(BaseModel):
    free_text: str = ""
    wizard: dict = {}


@router.post("/intake/parse", response_model=CourseSpec)
def intake_parse(req: IntakeRequest):
    return parse_intake(req.free_text, req.wizard)


@router.post("/courses")
def create_course(spec: CourseSpec, session: Session = Depends(get_session)):
    payload = generate_course_payload(spec)
    course = Course(**payload["course"])
    session.add(course)
    session.commit()
    session.refresh(course)

    week_map = {}
    for w in payload["weeks"]:
        week = Week(course_id=course.id, index=w["index"], objectives_json=json.dumps(w["objectives"]))
        session.add(week)
        session.commit()
        session.refresh(week)
        week_map[w["index"]] = week.id

    for l in payload["lessons"]:
        lesson = Lesson(
            course_id=course.id,
            week_id=week_map[l["week_index"]],
            day_index=l["day_index"],
            title=l["title"],
            content_md=l["content_md"],
            exercises_json=json.dumps(l["exercises"]),
            quiz_json=json.dumps(l["quiz"]),
        )
        session.add(lesson)
        session.commit()
        session.refresh(lesson)
        for ex in l["exercises"]:
            session.add(Task(lesson_id=lesson.id, label=ex))

    for c in payload["flashcards"]:
        session.add(Flashcard(course_id=course.id, front=c["front"], back=c["back"], tags_json=json.dumps(c["tags"])))

    session.commit()
    return {"course_id": course.id}


@router.get("/courses")
def list_courses(session: Session = Depends(get_session)):
    return session.exec(select(Course)).all()


@router.get("/courses/{course_id}")
def get_course(course_id: int, session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    weeks = session.exec(select(Week).where(Week.course_id == course_id)).all()
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
    return {"course": course, "weeks": weeks, "lessons": lessons}


@router.get("/courses/{course_id}/today")
def today(course_id: int, session: Session = Depends(get_session)):
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
    if not lessons:
        raise HTTPException(404, "No lessons")
    now = datetime.utcnow()
    idx = (now.timetuple().tm_yday % len(lessons))
    lesson = lessons[idx]
    tasks = session.exec(select(Task).where(Task.lesson_id == lesson.id)).all()
    return {"lesson": lesson, "tasks": tasks}


@router.get("/courses/{course_id}/certificate.html", response_class=HTMLResponse)
def cert_html(course_id: int, recipient_name: str = Query("Learner"), session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    cert = Certificate(course_id=course_id, recipient_name=recipient_name, hours_estimate=24)
    session.add(cert)
    session.commit()
    return f"<html><body><h1>Certificate of Completion</h1><p>{recipient_name} completed {course.title}</p></body></html>"


@router.get("/courses/{course_id}/certificate.pdf")
def cert_pdf(course_id: int, recipient_name: str = Query("Learner"), session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    out = io.BytesIO()
    p = canvas.Canvas(out)
    p.setFont("Helvetica", 20)
    p.drawString(72, 750, "Certificate of Completion")
    p.setFont("Helvetica", 14)
    p.drawString(72, 710, f"{recipient_name} completed {course.title}")
    p.showPage(); p.save()
    return Response(out.getvalue(), media_type="application/pdf")


@router.post("/export/course/{course_id}")
def export_course(course_id: int, session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
    export_dir = Path("server/data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    zpath = export_dir / f"course_{course_id}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("course.json", json.dumps(course.model_dump(), default=str, indent=2))
        for l in lessons:
            zf.writestr(f"lessons/{l.id}.md", l.content_md)
    return {"file": str(zpath)}


@router.post("/publish/coevo/{course_id}")
def publish(course_id: int, session: Session = Depends(get_session)):
    if not settings.coevo_url or not settings.coevo_api_key:
        raise HTTPException(400, "Set COEVO_URL and COEVO_API_KEY to enable publish. Export-only is available by default.")
    if settings.growora_network_mode == "offline" and ("localhost" not in settings.coevo_url and "127.0.0.1" not in settings.coevo_url):
        raise HTTPException(400, "Offline mode blocks non-localhost publish targets")

    exp = export_course(course_id, session)
    with open(exp["file"], "rb") as f:
        files = {"file": (Path(exp["file"]).name, f, "application/zip")}
        headers = {"Authorization": f"Bearer {settings.coevo_api_key}"}
        r = httpx.post(settings.coevo_url, headers=headers, files=files, timeout=30)
        r.raise_for_status()
    return {"ok": True, "status": "published", "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}
