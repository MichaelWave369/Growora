import json
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Lesson, QuizAttempt

router = APIRouter(prefix="/api", tags=["quizzes"])


class GradeRequest(BaseModel):
    answers: list


@router.get("/quizzes/{lesson_id}")
def get_quiz(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return json.loads(lesson.quiz_json)


@router.post("/quizzes/{lesson_id}/grade")
def grade_quiz(lesson_id: int, req: GradeRequest, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    quiz = json.loads(lesson.quiz_json)
    questions = quiz.get("questions", [])
    score = 0
    for i, q in enumerate(questions):
        if i < len(req.answers):
            ans = req.answers[i]
            if q.get("type") == "mcq" and ans == q.get("answer"):
                score += 1
            elif q.get("type") == "short" and str(ans).strip():
                score += 1
    attempt = QuizAttempt(lesson_id=lesson_id, score=score, total=len(questions))
    session.add(attempt); session.commit()
    return {"score": score, "total": len(questions)}
