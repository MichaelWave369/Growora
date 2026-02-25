from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Flashcard, ReviewLog
from app.services.srs import SM2State, sm2_review

router = APIRouter(prefix="/api", tags=["flashcards"])


class ReviewRequest(BaseModel):
    flashcard_id: int
    rating: int


@router.get("/flashcards/due")
def due(course_id: int = Query(...), session: Session = Depends(get_session)):
    cards = session.exec(select(Flashcard).where(Flashcard.course_id == course_id)).all()
    due_cards = []
    for c in cards:
        logs = session.exec(select(ReviewLog).where(ReviewLog.flashcard_id == c.id)).all()
        if not logs:
            due_cards.append(c)
            continue
        latest = sorted(logs, key=lambda l: l.reviewed_at)[-1]
        if latest.due_at <= datetime.utcnow():
            due_cards.append(c)
    return due_cards


@router.post("/flashcards/review")
def review(req: ReviewRequest, session: Session = Depends(get_session)):
    card = session.get(Flashcard, req.flashcard_id)
    if not card:
        raise HTTPException(404, "Flashcard not found")
    logs = session.exec(select(ReviewLog).where(ReviewLog.flashcard_id == card.id)).all()
    if logs:
        latest = sorted(logs, key=lambda l: l.reviewed_at)[-1]
        state = SM2State(repetitions=2 if latest.interval_days >= 6 else 1, interval_days=latest.interval_days, ease=latest.ease)
    else:
        state = SM2State()
    state, due_at = sm2_review(state, req.rating)
    log = ReviewLog(
        flashcard_id=card.id,
        rating=req.rating,
        interval_days=state.interval_days,
        ease=state.ease,
        due_at=due_at,
    )
    session.add(log)
    session.commit()
    return {"due_at": due_at, "interval_days": state.interval_days, "ease": state.ease}
