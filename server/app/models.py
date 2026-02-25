from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    topic: str
    learner_profile_json: str
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
    title: str
    content_md: str
    exercises_json: str
    quiz_json: str


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True)
    label: str
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


class Certificate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True)
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    recipient_name: str
    hours_estimate: int
