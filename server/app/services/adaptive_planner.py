import json
from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.models import Course, Lesson, QuizAttempt, Task


def _logical_now(day_start_time: str) -> datetime:
    now = datetime.utcnow()
    h, m = map(int, day_start_time.split(":"))
    day_start = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now < day_start:
        return now - timedelta(days=1)
    return now


def build_today_plan(course: Course, session: Session):
    logical_now = _logical_now(course.day_start_time)
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course.id).order_by(Lesson.order_index, Lesson.id)).all()
    tasks = session.exec(select(Task)).all()
    tasks = [t for t in tasks if any(l.id == t.lesson_id for l in lessons)]

    unfinished = [t for t in tasks if not t.done_at]
    rollover = unfinished[:2]
    current = unfinished[2:6]

    attempts = session.exec(select(QuizAttempt).join(Lesson, QuizAttempt.lesson_id == Lesson.id).where(Lesson.course_id == course.id)).all()
    avg_score = (sum(a.score / max(a.total, 1) for a in attempts) / len(attempts)) if attempts else 0.7

    blocks = [{"type": "task", "label": t.label, "minutes": t.estimated_minutes, "rollover": t in rollover} for t in rollover + current]
    if avg_score < 0.6:
        blocks.append({"type": "review", "label": "Extra repetition block", "minutes": 10})
        blocks.append({"type": "easy-variant", "label": "Easier variation task", "minutes": 10})
    elif avg_score > 0.85:
        blocks.append({"type": "challenge", "label": "Challenge extension", "minutes": 10})

    budget = course.minutes_per_day
    used = 0
    trimmed = []
    for b in blocks:
        if used + b["minutes"] <= budget:
            trimmed.append(b)
            used += b["minutes"]
    return {
        "day_anchor": logical_now.date().isoformat(),
        "time_budget": budget,
        "used_minutes": used,
        "rolled_over_count": len(rollover),
        "avg_quiz_score": round(avg_score, 3),
        "tasks": trimmed,
    }


def build_next7(course: Course, session: Session):
    today = build_today_plan(course, session)
    now = datetime.utcnow().date()
    preview = []
    for i in range(7):
        d = now + timedelta(days=i)
        preview.append({"date": d.isoformat(), "planned_minutes": today["time_budget"], "focus": "Practice + review" if i % 2 else "Core lesson"})
    return preview
