from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Lesson, Task

router = APIRouter(prefix="/api", tags=["progress"])


class CompleteRequest(BaseModel):
    task_id: int


@router.post("/progress/complete")
def complete(req: CompleteRequest, session: Session = Depends(get_session)):
    task = session.get(Task, req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.done_at = datetime.utcnow()
    session.add(task)
    session.commit()
    return {"ok": True}


@router.get("/progress/summary")
def summary(course_id: int = Query(...), session: Session = Depends(get_session)):
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
    lesson_ids = [l.id for l in lessons]
    tasks = session.exec(select(Task)).all()
    tasks = [t for t in tasks if t.lesson_id in lesson_ids]
    done = sum(1 for t in tasks if t.done_at)
    total = len(tasks) or 1
    return {
        "completion_percent": round(done * 100 / total, 2),
        "streak": 1 if done else 0,
        "mastery": round(done * 100 / total, 2),
    }
