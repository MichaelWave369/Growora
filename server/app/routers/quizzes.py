import json
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import Session

from app.db import get_session
from app.models import Lesson, QuizAttempt
from app.services.profile_context import resolve_profile_id
from app.services.mastery import update_mastery

router = APIRouter(prefix="/api", tags=["quizzes"])


class GradeRequest(BaseModel):
    answers: list


@router.get("/quizzes/{lesson_id}")
def get_quiz(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson: raise HTTPException(404, "Lesson not found")
    return json.loads(lesson.quiz_json)


@router.post("/quizzes/{lesson_id}/grade")
def grade_quiz(lesson_id: int, req: GradeRequest, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    lesson = session.get(Lesson, lesson_id)
    if not lesson: raise HTTPException(404, "Lesson not found")
    quiz = json.loads(lesson.quiz_json); questions = quiz.get("questions", [])
    score = 0
    for i, q in enumerate(questions):
        if i < len(req.answers):
            ans = req.answers[i]
            score += 1 if (q.get("type") == "mcq" and ans == q.get("answer")) or (q.get("type") == "short" and str(ans).strip()) else 0
    session.add(QuizAttempt(profile_id=profile_id, lesson_id=lesson_id, score=score, total=len(questions))); session.commit()
    cscore = score / max(len(questions), 1)
    # naive concept mapping: concept_id aligned to lesson id if exists
    update_mastery(session, profile_id, lesson.course_id, lesson_id, "quiz", cscore, {"lesson_id": lesson_id})
    return {"score": score, "total": len(questions)}
