from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import Course, Lesson, QuizAttempt, StudySession, Task
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix="/api", tags=["progress"])


class CompleteRequest(BaseModel):
    task_id: int


@router.post("/progress/complete")
def complete(req: CompleteRequest, session: Session = Depends(get_session)):
    task = session.get(Task, req.task_id)
    if not task: raise HTTPException(404, "Task not found")
    task.done_at = datetime.utcnow(); session.add(task); session.commit(); return {"ok": True}


@router.get("/progress/summary")
def summary(course_id: int = Query(...), request: Request = None, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    course = session.get(Course, course_id)
    if not course or course.profile_id != profile_id: raise HTTPException(404, "Course not found")
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all(); lesson_ids = [l.id for l in lessons]
    tasks = [t for t in session.exec(select(Task)).all() if t.lesson_id in lesson_ids]
    attempts = [a for a in session.exec(select(QuizAttempt).where(QuizAttempt.profile_id == profile_id)).all() if a.lesson_id in lesson_ids]
    done, total = sum(1 for t in tasks if t.done_at), len(tasks) or 1
    done_dates = sorted({t.done_at.date() for t in tasks if t.done_at}); streak=0; cursor=datetime.utcnow().date()
    while cursor in done_dates: streak += 1; cursor -= timedelta(days=1)
    missed_days = max(0, (datetime.utcnow().date() - min(done_dates)).days - len(done_dates)) if done_dates else 0
    avg_quiz = round(sum(a.score / max(a.total, 1) for a in attempts) / len(attempts), 3) if attempts else 0
    return {"completion_percent": round(done * 100 / total, 2), "streak": streak, "mastery": round((done * 0.5 + avg_quiz * 100 * 0.5), 2), "missed_days": missed_days, "avg_quiz_score": avg_quiz}


@router.get('/streak')
def streak(course_id: int = Query(...), request: Request = None, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    sessions = session.exec(select(StudySession).where(StudySession.profile_id == profile_id, StudySession.course_id == course_id, StudySession.ended_at != None)).all()
    dates = sorted({s.ended_at.date() for s in sessions if s.ended_at})
    current, best = 0, 0
    prev = None
    for d in dates:
        if prev and (d - prev).days == 1: current += 1
        else: current = 1
        best = max(best, current); prev = d
    return {"current_streak": current if dates and dates[-1] >= datetime.utcnow().date() - timedelta(days=1) else 0, "best_streak": best, "session_days": len(dates)}
