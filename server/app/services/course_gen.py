import json
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.services.nevora_engine import build_flashcards, build_quiz, build_worksheet


class CourseSpec(BaseModel):
    topic: str
    goal: str
    level: str = "beginner"
    schedule_days_per_week: int = Field(default=5, ge=5, le=7)
    daily_minutes: int = Field(default=30, ge=15, le=90)
    constraints: str = ""
    learner_type: str = "adult"
    preferred_style: str = "guided"
    day_starts_at: str = "06:00"
    free_text: str = ""


def parse_intake(free_text: str, wizard: dict) -> CourseSpec:
    merged = {**wizard, "free_text": free_text}
    merged.setdefault("topic", free_text.split(" ")[1] if free_text else "General Learning")
    merged.setdefault("goal", "Build confidence and consistency")
    return CourseSpec(**merged)


def generate_course_payload(spec: CourseSpec):
    weeks = []
    lessons = []
    lesson_counter = 1
    start_anchor = datetime.utcnow()
    for week_idx in range(1, 9):
        objectives = [
            f"Understand week {week_idx} fundamentals of {spec.topic}",
            f"Complete a checkpoint for week {week_idx}",
        ]
        weeks.append({"index": week_idx, "objectives": objectives})
        for day_idx in range(1, spec.schedule_days_per_week + 1):
            worksheet = build_worksheet(spec.topic, spec.level, day_idx)
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
        },
        "weeks": weeks,
        "lessons": lessons,
        "flashcards": cards,
    }
