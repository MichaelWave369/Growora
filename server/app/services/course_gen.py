import json
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models import DocumentChunk
from app.services.nevora_engine import build_flashcards, build_quiz, build_worksheet


class CourseSpec(BaseModel):
    topic: str
    goal: str
    level: str = "beginner"
    schedule_days_per_week: int = Field(default=5, ge=5, le=7)
    daily_minutes: int = Field(default=30, ge=15, le=120)
    constraints: str = ""
    learner_type: str = "adult"
    preferred_style: str = "guided"
    day_starts_at: str = "06:00"
    free_text: str = ""
    auto_use_library: bool = False
    context_doc_ids: list[int] = []


def parse_intake(free_text: str, wizard: dict) -> CourseSpec:
    merged = {**wizard, "free_text": free_text}
    merged.setdefault("topic", (free_text.split(" ")[1] if free_text and len(free_text.split()) > 1 else "General Learning"))
    merged.setdefault("goal", "Build confidence and consistency")
    return CourseSpec(**merged)


def _library_context(spec: CourseSpec, session: Session) -> str:
    if not spec.auto_use_library and not spec.context_doc_ids:
        return ""
    stmt = select(DocumentChunk)
    if spec.context_doc_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(spec.context_doc_ids))
    chunks = session.exec(stmt.limit(5)).all()
    if not chunks:
        return ""
    corpus = "\n".join(c.text[:220] for c in chunks)
    return f"\n\n## Library Key points\n- {corpus[:300]}\n\n## Vocabulary\n- 3 terms from your docs\n\n## Practice prompts\n- Apply one idea from your docs today"


def generate_course_payload(spec: CourseSpec, session: Session):
    weeks = []
    lessons = []
    lesson_counter = 1
    start_anchor = datetime.utcnow()
    lib_ctx = _library_context(spec, session)

    for week_idx in range(1, 9):
        objectives = [
            f"Understand week {week_idx} fundamentals of {spec.topic}",
            f"Complete a checkpoint for week {week_idx}",
        ]
        weeks.append({"index": week_idx, "objectives": objectives})
        for day_idx in range(1, spec.schedule_days_per_week + 1):
            worksheet = build_worksheet(spec.topic, spec.level, day_idx) + lib_ctx
            quiz = build_quiz(spec.topic)
            lessons.append(
                {
                    "temp_id": lesson_counter,
                    "week_index": week_idx,
                    "day_index": day_idx,
                    "title": f"Week {week_idx} Day {day_idx}: {spec.topic} practice",
                    "content_md": worksheet,
                    "exercises": [
                        f"Practice {spec.topic} for {spec.daily_minutes} minutes",
                        "Write a short reflection",
                    ],
                    "quiz": quiz,
                    "planned_at": (start_anchor + timedelta(days=lesson_counter - 1)).isoformat(),
                }
            )
            lesson_counter += 1

    cards = build_flashcards(spec.topic, count=12)
    return {
        "course": {
            "title": f"8-week {spec.topic} course",
            "topic": spec.topic,
            "learner_profile_json": json.dumps(spec.model_dump()),
            "day_start_time": spec.day_starts_at,
            "days_per_week": spec.schedule_days_per_week,
            "minutes_per_day": spec.daily_minutes,
            "difficulty": spec.level,
            "auto_use_library": spec.auto_use_library,
            "context_doc_ids_json": json.dumps(spec.context_doc_ids),
        },
        "weeks": weeks,
        "lessons": lessons,
        "flashcards": cards,
    }
