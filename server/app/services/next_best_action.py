from datetime import datetime
from sqlmodel import Session, select

from app.models import Concept, Course, MasteryState, Task, Lesson
from app.services.mastery import due_at


def next_best(session: Session, course: Course):
    mastery = session.exec(select(MasteryState).where(MasteryState.profile_id == course.profile_id, MasteryState.course_id == course.id)).all()
    concepts = session.exec(select(Concept).where(Concept.profile_id == course.profile_id, Concept.course_id == course.id)).all()
    due = [m for m in mastery if due_at(m.theta, m.last_seen_at) <= datetime.utcnow()]
    weak = sorted(mastery, key=lambda x: x.theta)[:3]

    lessons = session.exec(select(Lesson).where(Lesson.course_id == course.id).order_by(Lesson.order_index, Lesson.id)).all()
    tasks = session.exec(select(Task)).all()
    task_pool = [t for t in tasks if any(l.id == t.lesson_id for l in lessons) and not t.done_at]

    budget = course.minutes_per_day
    blocks = [
        {"type": "review", "minutes": min(10, max(5, budget // 4)), "label": f"Review {len(due)} due concepts"},
        {"type": "focus", "minutes": min(20, max(10, budget // 2)), "label": task_pool[0].label if task_pool else "Focused practice"},
        {"type": "interleave", "minutes": min(8, max(3, budget // 6)), "label": "Interleaved weak concept drill"},
    ]
    if weak and weak[0].theta > 1.2:
        blocks.append({"type": "challenge", "minutes": 6, "label": "Challenge extension"})

    used, trimmed = 0, []
    for b in blocks:
        if used + b["minutes"] <= budget:
            trimmed.append(b); used += b["minutes"]

    explain = [
        f"{len(due)} concepts are due for review.",
        f"Weak concepts prioritized: {', '.join(str(w.concept_id) for w in weak[:2]) or 'none'}.",
        "Interleaving added to improve retention.",
    ]
    next7 = [{"day": i+1, "minutes": budget, "focus": "review+practice"} for i in range(7)]
    return {"today_plan": trimmed, "time_budget": budget, "used_minutes": used, "explanations": explain, "next7": next7, "due_count": len(due), "concept_count": len(concepts)}
