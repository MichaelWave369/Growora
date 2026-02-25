from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str
    role: str = "adult"
    timezone: str = "UTC"
    day_start_time: str = "06:00"
    pin_hash_optional: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
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
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    front: str
    back: str
    tags_json: str = "[]"


class ReviewLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    flashcard_id: int = Field(index=True)
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    rating: int
    interval_days: int
    ease: float
    due_at: datetime


class QuizAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    lesson_id: int = Field(index=True)
    score: int
    total: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Certificate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    recipient_name: str
    hours_estimate: int


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    filename: str
    mime: str
    size: int
    sha256: str
    tags_json: str = "[]"
    extraction_error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    document_id: int = Field(index=True)
    idx: int
    text: str
    page: int = 0
    meta_json: str = "{}"


class PublishLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    provider: str
    status: str
    detail: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StudySession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    lesson_id_optional: int | None = Field(default=None, index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    planned_minutes: int = 30
    actual_minutes: int = 0
    mode: str = "standard"
    notes_md: str = ""


class SessionEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    type: str
    payload_json: str = "{}"


class SessionSummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    focus_score: float = 0.0
    mastery_delta: float = 0.0
    streak_delta: int = 0
    coach_summary_md: str = ""


class ForgeJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    status: str = "done"
    type: str
    input_doc_ids_json: str
    params_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    result_ref_json: str = "{}"
    error: str | None = None


class TutorMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int | None = Field(default=None, index=True)
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SchemaVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = "0.3.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Concept(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    slug: str = Field(index=True)
    title: str
    description: str = ""
    tags_json: str = "[]"
    meta_json: str = "{}"


class ConceptEdge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    src_concept_id: int = Field(index=True)
    dst_concept_id: int = Field(index=True)
    kind: str = "prereq"
    weight: float = 1.0


class ConceptLessonLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    concept_id: int = Field(index=True)
    lesson_id: int = Field(index=True)
    strength: float = 1.0


class MasteryState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    concept_id: int = Field(index=True)
    theta: float = 0.0
    sigma: float = 1.0
    last_seen_at: datetime | None = None
    streak: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    concept_id: int = Field(index=True)
    kind: str = "quiz"
    score: float = 0.0
    ts: datetime = Field(default_factory=datetime.utcnow)
    meta_json: str = "{}"


class Microdrill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    course_id: int = Field(index=True)
    concept_id: int = Field(index=True)
    kind: str
    prompt: str
    answer_key_json: str = "{}"
    difficulty: str = "beginner"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(index=True)
    kind: str
    status: str = "queued"
    detail: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Classroom(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id_owner: int = Field(index=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClassroomMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    classroom_id: int = Field(index=True)
    profile_id: int = Field(index=True)
    role: str = "learner"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClassroomSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    classroom_id: int = Field(index=True)
    course_id: int = Field(index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    mode: str = "live"
    title: str = "Classroom Session"
    agenda_json: str = "[]"
    notes_md: str = ""


class ClassroomSessionMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    profile_id: int = Field(index=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: datetime | None = None
    state_json: str = "{}"


class ClassroomEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    type: str
    payload_json: str = "{}"


class Assignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    profile_id: int = Field(index=True)
    kind: str
    ref_id: int
    status: str = "assigned"
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    score: float | None = None


class SlideDeck(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    title: str
    slides_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LiveQuiz(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    title: str
    questions_json: str
    concept_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "draft"


class LiveQuizResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    live_quiz_id: int = Field(index=True)
    profile_id: int = Field(index=True)
    answers_json: str
    score: float
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class TeachbackPrompt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    concept_id: int = Field(index=True)
    prompt: str
    rubric_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TeachbackSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_id: int = Field(index=True)
    profile_id: int = Field(index=True)
    response_text: str
    score_json: str
    feedback_md: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class LanRoom(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    classroom_id: int = Field(index=True)
    session_id: int = Field(index=True)
    code: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    created_by_profile_id: int = Field(index=True)
    status: str = "active"


class LanClient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(index=True)
    client_name: str
    device_type: str = "unknown"
    ip: str = ""
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    role: str = "learner"
    profile_id_optional: int | None = Field(default=None, index=True)
    permissions_json: str = "{}"
    status: str = "pending"


class LanAuthToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(index=True)
    token_hash: str = Field(index=True)
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    client_id: int = Field(index=True)
