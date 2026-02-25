import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Concept, ConceptEdge, Course, MasteryState
from app.services.concepts import rebuild_graph
from app.services.jobs import complete, enqueue
from app.services.mastery import bucket, due_at, update_mastery
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix='/api', tags=['graph'])


@router.post('/graph/rebuild')
def graph_rebuild(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Course, course_id)
    if not c or c.profile_id != pid: raise HTTPException(404, 'Course not found')
    j = enqueue(session, pid, 'graph_rebuild', f'course={course_id}')
    out = rebuild_graph(session, pid, course_id)
    complete(session, j.id, 'done', str(out))
    return {'job_id': j.id, **out}


@router.get('/graph')
def graph(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    concepts = session.exec(select(Concept).where(Concept.profile_id == pid, Concept.course_id == course_id)).all()
    edges = session.exec(select(ConceptEdge).where(ConceptEdge.profile_id == pid, ConceptEdge.course_id == course_id)).all()
    mastery = session.exec(select(MasteryState).where(MasteryState.profile_id == pid, MasteryState.course_id == course_id)).all()
    by_concept = {m.concept_id: {'theta': m.theta, 'bucket': bucket(m.theta), 'due_at': due_at(m.theta, m.last_seen_at).isoformat()} for m in mastery}
    return {'concepts': concepts, 'edges': edges, 'mastery': by_concept}


class ConceptPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    tags_json: list[str] | None = None


@router.patch('/graph/concepts/{concept_id}')
def patch_concept(concept_id: int, body: ConceptPatch, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Concept, concept_id)
    if not c or c.profile_id != pid: raise HTTPException(404, 'Concept not found')
    d = body.model_dump(exclude_none=True)
    if 'tags_json' in d: d['tags_json'] = json.dumps(d['tags_json'])
    for k, v in d.items(): setattr(c, k, v)
    session.add(c); session.commit(); return {'ok': True}


class EdgeBody(BaseModel):
    course_id: int
    src_concept_id: int
    dst_concept_id: int
    kind: str = 'prereq'
    weight: float = 1.0


@router.post('/graph/edges')
def add_edge(body: EdgeBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    e = ConceptEdge(profile_id=pid, **body.model_dump())
    session.add(e); session.commit(); session.refresh(e); return e


@router.delete('/graph/edges/{edge_id}')
def del_edge(edge_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    e = session.get(ConceptEdge, edge_id)
    if not e or e.profile_id != pid: raise HTTPException(404, 'Edge not found')
    session.delete(e); session.commit(); return {'ok': True}


@router.get('/mastery')
def mastery(course_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    out=[]
    for m in session.exec(select(MasteryState).where(MasteryState.profile_id == pid, MasteryState.course_id == course_id)).all():
        out.append({'id': m.id, 'concept_id': m.concept_id, 'theta': m.theta, 'bucket': bucket(m.theta), 'due_at': due_at(m.theta, m.last_seen_at).isoformat()})
    return out


class EvidenceBody(BaseModel):
    course_id: int
    concept_id: int
    kind: str = 'quiz'
    score: float
    meta_json: dict = {}


@router.post('/mastery/evidence')
def evidence(body: EvidenceBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    st = update_mastery(session, pid, body.course_id, body.concept_id, body.kind, body.score, body.meta_json)
    return {'concept_id': st.concept_id, 'theta': st.theta, 'bucket': bucket(st.theta)}
