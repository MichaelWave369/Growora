import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Concept, MasteryState, Microdrill
from app.services.mastery import due_at, update_mastery
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix='/api', tags=['drills'])


@router.get('/drills/due')
def due(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    out=[]
    for m in session.exec(select(MasteryState).where(MasteryState.profile_id == pid, MasteryState.course_id == course_id)).all():
        if due_at(m.theta, m.last_seen_at):
            drills = session.exec(select(Microdrill).where(Microdrill.profile_id == pid, Microdrill.course_id == course_id, Microdrill.concept_id == m.concept_id)).all()
            out.extend(drills[:2])
    return out


class GenBody(BaseModel):
    course_id: int
    concept_id: int
    count: int = 3
    difficulty: str = 'beginner'


@router.post('/drills/generate')
def generate(body: GenBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Concept, body.concept_id)
    if not c or c.profile_id != pid: raise HTTPException(404, 'Concept not found')
    items=[]
    for i in range(max(1,min(10,body.count))):
        d = Microdrill(profile_id=pid, course_id=body.course_id, concept_id=body.concept_id, kind='recall', prompt=f"Explain {c.title} in one sentence ({i+1})", answer_key_json=json.dumps({'rubric':'mentions core idea'}), difficulty=body.difficulty)
        session.add(d); items.append(d)
    session.commit()
    for d in items:
        session.refresh(d)
    return items


class GradeBody(BaseModel):
    drill_id: int
    user_answer: str
    score: float


@router.post('/drills/grade')
def grade(body: GradeBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    d = session.get(Microdrill, body.drill_id)
    if not d or d.profile_id != pid: raise HTTPException(404, 'Drill not found')
    st = update_mastery(session, pid, d.course_id, d.concept_id, 'exercise', max(0,min(1,body.score)), {'answer': body.user_answer[:200]})
    return {'ok': True, 'theta': st.theta}
