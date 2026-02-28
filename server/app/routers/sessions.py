import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Course, SessionEvent, SessionSummary, StudySession
from app.services.coach_engine import coach_message
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix="/api", tags=["sessions"])


class StartBody(BaseModel):
    course_id: int
    lesson_id_optional: int | None = None
    planned_minutes: int = 30
    mode: str = "standard"


class EventBody(BaseModel):
    session_id: int
    type: str
    payload: dict = {}


class EndBody(BaseModel):
    session_id: int
    notes_md: str = ""


@router.post('/sessions/start')
def start_session(body: StartBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Course, body.course_id)
    if not c or c.profile_id != profile_id:
        raise HTTPException(404, 'Course not found')
    s = StudySession(profile_id=profile_id, course_id=body.course_id, lesson_id_optional=body.lesson_id_optional, planned_minutes=body.planned_minutes, mode=body.mode)
    session.add(s); session.commit(); session.refresh(s)
    session.add(SessionEvent(session_id=s.id, type='start', payload_json=json.dumps({'mode': body.mode}))); session.commit(); session.refresh(s)
    return s


@router.post('/sessions/event')
def add_event(body: EventBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    s = session.get(StudySession, body.session_id)
    if not s or s.profile_id != profile_id:
        raise HTTPException(404, 'Session not found')
    e = SessionEvent(session_id=s.id, type=body.type, payload_json=json.dumps(body.payload))
    session.add(e); session.commit(); return {'ok': True}


@router.post('/sessions/end')
def end_session(body: EndBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    s = session.get(StudySession, body.session_id)
    if not s or s.profile_id != profile_id:
        raise HTTPException(404, 'Session not found')
    s.ended_at = datetime.utcnow(); s.notes_md = body.notes_md
    s.actual_minutes = max(1, int((s.ended_at - s.started_at).total_seconds() // 60))
    session.add(s)
    events = session.exec(select(SessionEvent).where(SessionEvent.session_id == s.id)).all()
    wrong = sum(1 for e in events if e.type == 'quiz_wrong')
    quick = wrong >= 3
    msg = coach_message(0, 0.7, s.actual_minutes / max(s.planned_minutes, 1), 1, quick)
    session.add(SessionSummary(session_id=s.id, focus_score=0.7, mastery_delta=0.1, streak_delta=1, coach_summary_md=msg))
    session.commit()
    return {'ok': True, 'session_id': s.id}


@router.get('/sessions/recent')
def recent(course_id: int = Query(...), request: Request = None, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    return session.exec(select(StudySession).where(StudySession.profile_id == profile_id, StudySession.course_id == course_id).order_by(StudySession.started_at.desc()).limit(20)).all()


@router.get('/sessions/{session_id}')
def get_session_detail(session_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    s = session.get(StudySession, session_id)
    if not s or s.profile_id != profile_id: raise HTTPException(404, 'Session not found')
    events = session.exec(select(SessionEvent).where(SessionEvent.session_id == session_id).order_by(SessionEvent.ts)).all()
    summary = session.exec(select(SessionSummary).where(SessionSummary.session_id == session_id)).first()
    return {'session': s, 'events': events, 'summary': summary}


@router.get('/dashboard/analytics')
def analytics(request: Request, course_id: int | None = None, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    stmt = select(StudySession).where(StudySession.profile_id == profile_id)
    if course_id:
        stmt = stmt.where(StudySession.course_id == course_id)
    sessions = session.exec(stmt).all()
    weekly_minutes = sum(s.actual_minutes for s in sessions if s.ended_at)
    mastery_trend = [0.55 + i * 0.02 for i in range(min(8, len(sessions) + 1))]
    return {'weekly_minutes': weekly_minutes, 'session_count': len(sessions), 'mastery_trend': mastery_trend, 'streaks': {'current': min(len(sessions), 7)}}
