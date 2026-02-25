from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import Flashcard, ReviewLog
from app.services.profile_context import resolve_profile_id
from app.services.srs import SM2State, sm2_review
from app.services.mastery import update_mastery

router = APIRouter(prefix="/api", tags=["flashcards"])


class ReviewRequest(BaseModel):
    flashcard_id: int
    rating: int


@router.get("/flashcards/due")
def due(request: Request, course_id: int = Query(...), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    cards = session.exec(select(Flashcard).where(Flashcard.course_id == course_id, Flashcard.profile_id == profile_id)).all()
    due_cards = []
    for c in cards:
        logs = session.exec(select(ReviewLog).where(ReviewLog.flashcard_id == c.id, ReviewLog.profile_id == profile_id)).all()
        if not logs:
            due_cards.append(c); continue
        latest = sorted(logs, key=lambda l: l.reviewed_at)[-1]
        if latest.due_at <= datetime.utcnow(): due_cards.append(c)
    return due_cards


@router.post("/flashcards/review")
def review(req: ReviewRequest, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    card = session.get(Flashcard, req.flashcard_id)
    if not card or card.profile_id != profile_id:
        raise HTTPException(404, "Flashcard not found")
    logs = session.exec(select(ReviewLog).where(ReviewLog.flashcard_id == card.id, ReviewLog.profile_id == profile_id)).all()
    state = SM2State(repetitions=2 if logs and logs[-1].interval_days >= 6 else 1 if logs else 0, interval_days=(logs[-1].interval_days if logs else 0), ease=(logs[-1].ease if logs else 2.5))
    state, due_at = sm2_review(state, req.rating)
    session.add(ReviewLog(profile_id=profile_id, flashcard_id=card.id, rating=req.rating, interval_days=state.interval_days, ease=state.ease, due_at=due_at)); session.commit()
    update_mastery(session, profile_id, card.course_id, card.id, "flashcard", req.rating / 5.0, {"flashcard_id": card.id})
    return {"due_at": due_at, "interval_days": state.interval_days, "ease": state.ease}
