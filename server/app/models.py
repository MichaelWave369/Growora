from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    topic: str
    learner_profile_json: str
    day_start_time: str = "06:00"
    days_per_week: int = 5
    minutes_per_day: int = 30
    difficulty: str = "beginner"
    auto_use_library: bool = False
    context_doc_ids_json: str = "[]"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Week(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True)
    index: int
    objectives_json: str


class Lesson(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True)
    week_id: int = Field(index=True)
    day_index: int
    order_index: int = 0
    title: str
    content_md: str
    exercises_json: str
    quiz_json: str
    estimated_minutes: int = 30
    difficulty: str = "beginner"
    user_edited: bool = False


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True)
    label: str
    estimated_minutes: int = 10
    done_at: Optional[datetime] = None


class Flashcard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True)
    front: str
    back: str
    tags_json: str = "[]"


class ReviewLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    flashcard_id: int = Field(index=True)
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    rating: int
    interval_days: int
    ease: float
    due_at: datetime


class QuizAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True)
    score: int
    total: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Certificate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True)
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    recipient_name: str
    hours_estimate: int


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    mime: str
    size: int
    sha256: str
    tags_json: str = "[]"
    extraction_error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(index=True)
    idx: int
    text: str
    page: int = 0
    meta_json: str = "{}"


class PublishLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True)
    provider: str
    status: str
    detail: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
