import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from sqlmodel import Session, select

from app.core.config import settings
from app.db import get_session
from app.models import Certificate, Course, Flashcard, Lesson, PublishLog, Task, Week, StudySession
from app.services.adaptive_planner import build_next7, build_today_plan
from app.services.course_gen import CourseSpec, generate_course_payload, parse_intake
from app.services.profile_context import resolve_profile_id
from app.services.publisher import publish_coevo
from app.services.triad369_packager import build_package, validate_package

router = APIRouter(prefix="/api", tags=["courses"])


class IntakeRequest(BaseModel):
    free_text: str = ""
    wizard: dict = {}


class CoursePatch(BaseModel):
    title: str | None = None
    day_start_time: str | None = None
    days_per_week: int | None = None
    minutes_per_day: int | None = None
    difficulty: str | None = None


class LessonPatch(BaseModel):
    title: str | None = None
    content_md: str | None = None
    exercises_json: list[str] | None = None
    order_index: int | None = None


class CourseSettings(BaseModel):
    day_start_time: str
    days_per_week: int
    minutes_per_day: int


def _get_course_owned(session: Session, course_id: int, profile_id: int):
    c = session.get(Course, course_id)
    if not c or c.profile_id != profile_id:
        raise HTTPException(404, "Course not found")
    return c


@router.post("/intake/parse", response_model=CourseSpec)
def intake_parse(req: IntakeRequest):
    return parse_intake(req.free_text, req.wizard)


@router.post("/courses")
def create_course(spec: CourseSpec, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    payload = generate_course_payload(spec, session, profile_id)
    course = Course(profile_id=profile_id, **payload["course"])
    session.add(course); session.commit(); session.refresh(course)

    week_map = {}
    for w in payload["weeks"]:
        week = Week(course_id=course.id, index=w["index"], objectives_json=json.dumps(w["objectives"]))
        session.add(week); session.commit(); session.refresh(week)
        week_map[w["index"]] = week.id

    for i, l in enumerate(payload["lessons"]):
        lesson = Lesson(course_id=course.id, week_id=week_map[l["week_index"]], day_index=l["day_index"], order_index=i, title=l["title"], content_md=l["content_md"], exercises_json=json.dumps(l["exercises"]), quiz_json=json.dumps(l["quiz"]), estimated_minutes=min(course.minutes_per_day, 30), difficulty=course.difficulty)
        session.add(lesson); session.commit(); session.refresh(lesson)
        for ex in l["exercises"]:
            session.add(Task(lesson_id=lesson.id, label=ex, estimated_minutes=10))

    for c in payload["flashcards"]:
        session.add(Flashcard(profile_id=profile_id, course_id=course.id, front=c["front"], back=c["back"], tags_json=json.dumps(c["tags"])))
    session.commit()
    return {"course_id": course.id}


@router.get("/courses")
def list_courses(request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    return session.exec(select(Course).where(Course.profile_id == profile_id)).all()


@router.get("/courses/{course_id}")
def get_course(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    weeks = session.exec(select(Week).where(Week.course_id == course_id)).all()
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order_index, Lesson.id)).all()
    return {"course": course, "weeks": weeks, "lessons": lessons}


@router.patch("/courses/{course_id}")
def patch_course(course_id: int, req: CoursePatch, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(course, k, v)
    session.add(course); session.commit()
    return {"ok": True}


@router.patch("/lessons/{lesson_id}")
def patch_lesson(lesson_id: int, req: LessonPatch, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    _get_course_owned(session, lesson.course_id, profile_id)
    data = req.model_dump(exclude_none=True)
    if "exercises_json" in data:
        data["exercises_json"] = json.dumps(data["exercises_json"])
    for k, v in data.items(): setattr(lesson, k, v)
    lesson.user_edited = True
    session.add(lesson); session.commit()
    return {"ok": True}


@router.post("/courses/{course_id}/regen/week/{week_index}")
def regen_week(course_id: int, week_index: int, request: Request, overwrite_user_edits: bool = False, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    week = session.exec(select(Week).where(Week.course_id == course_id, Week.index == week_index)).first()
    if not week: raise HTTPException(404, "Week not found")
    lessons = session.exec(select(Lesson).where(Lesson.week_id == week.id)).all()
    for lesson in lessons:
        if lesson.user_edited and not overwrite_user_edits:
            continue
        lesson.content_md = f"# Regenerated\n\n{lesson.title}\n\nUpdated for difficulty: {course.difficulty}"
        session.add(lesson)
    session.commit(); return {"ok": True}


@router.post("/courses/{course_id}/settings")
def update_settings(course_id: int, req: CourseSettings, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    course.day_start_time, course.days_per_week, course.minutes_per_day = req.day_start_time, req.days_per_week, req.minutes_per_day
    session.add(course); session.commit(); return {"ok": True}


@router.get("/courses/{course_id}/plan/today")
def plan_today(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    return build_today_plan(_get_course_owned(session, course_id, resolve_profile_id(session, x_growora_profile, request)), session)


@router.get("/courses/{course_id}/plan/next7")
def plan_next7(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    return build_next7(_get_course_owned(session, course_id, resolve_profile_id(session, x_growora_profile, request)), session)


@router.get("/courses/{course_id}/today")
def today_alias(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    return plan_today(course_id, request, session, x_growora_profile)


@router.get("/courses/{course_id}/certificate.html", response_class=HTMLResponse)
def cert_html(course_id: int, request: Request, recipient_name: str = Query("Learner"), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    cert = Certificate(profile_id=profile_id, course_id=course_id, recipient_name=recipient_name, hours_estimate=24)
    session.add(cert); session.commit(); session.refresh(cert)
    return f"<html><body><h1>Certificate of Completion</h1><p>ID: {cert.id}</p><p>Date: {cert.issued_at.date()}</p><p>{recipient_name} completed {course.title} ({cert.hours_estimate} hours)</p><p>Verify: /verify/{cert.id}</p></body></html>"


@router.get("/courses/{course_id}/certificate.pdf")
def cert_pdf(course_id: int, request: Request, recipient_name: str = Query("Learner"), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    cert = Certificate(profile_id=profile_id, course_id=course_id, recipient_name=recipient_name, hours_estimate=24)
    session.add(cert); session.commit(); session.refresh(cert)
    out = io.BytesIO(); p = canvas.Canvas(out)
    p.setFont("Helvetica", 20); p.drawString(72, 750, "Certificate of Completion")
    p.setFont("Helvetica", 12); p.drawString(72, 720, f"Certificate ID: {cert.id}")
    p.drawString(72, 700, f"Issued: {cert.issued_at.date()}")
    p.drawString(72, 680, f"{recipient_name} completed {course.title}")
    p.showPage(); p.save(); return Response(out.getvalue(), media_type="application/pdf")


@router.get("/verify/{cert_id}", response_class=HTMLResponse)
def verify_cert(cert_id: int, session: Session = Depends(get_session)):
    cert = session.get(Certificate, cert_id)
    if not cert: raise HTTPException(404, "Certificate not found")
    course = session.get(Course, cert.course_id)
    return f"<html><body><h1>Valid Certificate</h1><p>Certificate {cert.id} exists for {course.title}</p></body></html>"


@router.post("/export/triad369/{course_id}")
def export_triad(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    return {"file": str(build_package(_get_course_owned(session, course_id, resolve_profile_id(session, x_growora_profile, request)), session))}


@router.post("/import/triad369")
def import_triad(request: Request, file: UploadFile = File(...), restore_learning_record: bool = True, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    temp = Path("server/data/exports") / f"import_{file.filename}"; temp.write_bytes(file.file.read())
    val = validate_package(temp)
    if not val["ok"]: raise HTTPException(400, f"Invalid package: {val['errors']}")
    import zipfile
    with zipfile.ZipFile(temp, "r") as zf:
        c = json.loads(zf.read("course.json"))
        course = Course(profile_id=profile_id, title=f"Imported: {c['title']}", topic=c["topic"], learner_profile_json=c.get("learner_profile_json", "{}"), day_start_time=c.get("day_start_time", "06:00"), days_per_week=c.get("days_per_week", 5), minutes_per_day=c.get("minutes_per_day", 30), difficulty=c.get("difficulty", "beginner"))
        session.add(course); session.commit(); session.refresh(course)
        week = Week(course_id=course.id, index=1, objectives_json=json.dumps(["Imported objectives"]))
        session.add(week); session.commit(); session.refresh(week)
        lfs = [n for n in zf.namelist() if n.startswith("lessons/week") and n.endswith(".md")]
        for i, lf in enumerate(sorted(lfs), start=1):
            qf = lf.replace("lessons/", "lessons/quizzes/").replace(".md", ".quiz.json")
            lesson = Lesson(course_id=course.id, week_id=week.id, day_index=i, order_index=i, title=f"Imported lesson {i}", content_md=zf.read(lf).decode(), exercises_json=json.dumps(["Imported task"]), quiz_json=(zf.read(qf).decode() if qf in zf.namelist() else json.dumps({"questions": []})))
            session.add(lesson); session.commit(); session.refresh(lesson)
            session.add(Task(lesson_id=lesson.id, label="Imported task", estimated_minutes=10)); session.commit()
        for c in json.loads(zf.read("lessons/flashcards.json")) if "lessons/flashcards.json" in zf.namelist() else []:
            session.add(Flashcard(profile_id=profile_id, course_id=course.id, front=c.get("front", "Q"), back=c.get("back", "A"), tags_json=c.get("tags_json", "[]")))
        if restore_learning_record and "learning_record.json" in zf.namelist():
            rec = json.loads(zf.read("learning_record.json"))
            for s in rec.get("sessions", [])[:100]:
                session.add(StudySession(profile_id=profile_id, course_id=course.id, lesson_id_optional=s.get("lesson_id_optional"), planned_minutes=s.get("planned_minutes", 30), actual_minutes=s.get("actual_minutes", 0), mode=s.get("mode", "standard"), notes_md=s.get("notes_md", "")))
        session.commit()
    return {"course_id": course.id, "validation": val}


@router.post("/publish/coevo/{course_id}")
def publish(course_id: int, request: Request, dry_run: int = Query(1), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = _get_course_owned(session, course_id, profile_id)
    zpath = build_package(course, session)
    result = publish_coevo(zpath.read_bytes(), {"course_id": course.id, "title": course.title}, bool(dry_run))
    session.add(PublishLog(profile_id=profile_id, course_id=course.id, provider="coevo", status=result["status"], detail=result.get("detail", ""))); session.commit()
    if not result.get("ok"): raise HTTPException(400, result.get("detail", "publish failed"))
    return result


@router.get("/publish/logs")
def publish_logs(request: Request, course_id: int | None = None, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    stmt = select(PublishLog).where(PublishLog.profile_id == profile_id)
    if course_id: stmt = stmt.where(PublishLog.course_id == course_id)
    return session.exec(stmt).all()


@router.get("/publish/test")
def publish_test():
    return {"configured": bool(settings.coevo_url and settings.coevo_api_key), "network_mode": settings.growora_network_mode, "allowed_hosts": list(settings.allowed_hosts)}


@router.post("/export/triad369/validate")
def validate_triad(file: UploadFile = File(...)):
    temp = Path("server/data/exports") / f"validate_{file.filename}"; temp.write_bytes(file.file.read())
    return validate_package(temp)
