import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    Assignment,
    Classroom,
    ClassroomEvent,
    ClassroomMember,
    ClassroomSession,
    ClassroomSessionMember,
    Concept,
    Course,
    Lesson,
    LiveQuiz,
    LiveQuizResponse,
    SlideDeck,
    TeachbackPrompt,
    TeachbackSubmission,
)
from app.services.classroom import classroom_summary, create_deck_from_text, teachback_score, whiteboard_path
from app.services.mastery import update_mastery
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix='/api', tags=['classroom'])


class ClassroomBody(BaseModel):
    name: str


@router.post('/classrooms')
def create_classroom(body: ClassroomBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = Classroom(profile_id_owner=pid, name=body.name)
    session.add(c); session.commit(); session.refresh(c)
    session.add(ClassroomMember(classroom_id=c.id, profile_id=pid, role='facilitator')); session.commit()
    return c


@router.get('/classrooms')
def list_classrooms(request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    owned = session.exec(select(Classroom).where(Classroom.profile_id_owner == pid)).all()
    member = session.exec(select(ClassroomMember).where(ClassroomMember.profile_id == pid)).all()
    mids = {m.classroom_id for m in member}
    extra = session.exec(select(Classroom).where(Classroom.id.in_(mids))).all() if mids else []
    by_id = {c.id: c for c in owned + extra}
    return list(by_id.values())


class MemberBody(BaseModel):
    profile_id: int
    role: str = 'learner'


@router.post('/classrooms/{classroom_id}/members')
def add_member(classroom_id: int, body: MemberBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Classroom, classroom_id)
    if not c or c.profile_id_owner != pid: raise HTTPException(404, 'Classroom not found')
    m = ClassroomMember(classroom_id=classroom_id, profile_id=body.profile_id, role=body.role)
    session.add(m); session.commit(); session.refresh(m)
    return m


@router.delete('/classrooms/{classroom_id}/members/{member_id}')
def del_member(classroom_id: int, member_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Classroom, classroom_id)
    if not c or c.profile_id_owner != pid: raise HTTPException(404, 'Classroom not found')
    m = session.get(ClassroomMember, member_id)
    if not m or m.classroom_id != classroom_id: raise HTTPException(404, 'Member not found')
    session.delete(m); session.commit(); return {'ok': True}


class StartBody(BaseModel):
    course_id: int
    agenda: list[str] = []
    mode: str = 'live'
    title: str = 'Live class'


@router.post('/classrooms/{classroom_id}/sessions/start')
def start(classroom_id: int, body: StartBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = session.get(Classroom, classroom_id)
    if not c or c.profile_id_owner != pid: raise HTTPException(404, 'Classroom not found')
    course = session.get(Course, body.course_id)
    if not course: raise HTTPException(404, 'Course not found')
    s = ClassroomSession(classroom_id=classroom_id, course_id=body.course_id, mode=body.mode, title=body.title, agenda_json=json.dumps(body.agenda))
    session.add(s); session.commit(); session.refresh(s)
    session.add(ClassroomSessionMember(session_id=s.id, profile_id=pid)); session.commit()
    return s


class JoinBody(BaseModel):
    profile_id: int


@router.post('/classrooms/sessions/{session_id}/join')
def join(session_id: int, body: JoinBody, session: Session = Depends(get_session)):
    s = session.get(ClassroomSession, session_id)
    if not s: raise HTTPException(404, 'Session not found')
    m = ClassroomSessionMember(session_id=session_id, profile_id=body.profile_id)
    session.add(m); session.commit(); session.refresh(m); return m


class EventBody(BaseModel):
    type: str
    payload: dict = {}


@router.post('/classrooms/sessions/{session_id}/event')
def event(session_id: int, body: EventBody, session: Session = Depends(get_session)):
    if len(json.dumps(body.payload)) > 20000:
        raise HTTPException(400, 'Payload too large')
    e = ClassroomEvent(session_id=session_id, type=body.type, payload_json=json.dumps(body.payload))
    session.add(e); session.commit(); return {'ok': True}


@router.post('/classrooms/sessions/{session_id}/end')
def end(session_id: int, session: Session = Depends(get_session)):
    s = session.get(ClassroomSession, session_id)
    if not s: raise HTTPException(404, 'Session not found')
    s.ended_at = datetime.utcnow(); session.add(s)
    members = session.exec(select(ClassroomSessionMember).where(ClassroomSessionMember.session_id == session_id)).all()
    for m in members:
        if not m.left_at:
            m.left_at = datetime.utcnow(); session.add(m)
    session.commit(); return {'ok': True}


@router.get('/classrooms/sessions/{session_id}')
def detail(session_id: int, session: Session = Depends(get_session)):
    s = session.get(ClassroomSession, session_id)
    if not s: raise HTTPException(404, 'Session not found')
    members = session.exec(select(ClassroomSessionMember).where(ClassroomSessionMember.session_id == session_id)).all()
    events = session.exec(select(ClassroomEvent).where(ClassroomEvent.session_id == session_id).order_by(ClassroomEvent.ts.desc()).limit(200)).all()
    return {'session': s, 'members': members, 'agenda': json.loads(s.agenda_json or '[]'), 'events': events}


class AssignBody(BaseModel):
    profile_id: int
    kind: str
    ref_id: int


@router.post('/classrooms/sessions/{session_id}/assign')
def assign(session_id: int, body: AssignBody, session: Session = Depends(get_session)):
    a = Assignment(session_id=session_id, profile_id=body.profile_id, kind=body.kind, ref_id=body.ref_id)
    session.add(a); session.commit(); session.refresh(a); return a


class CompleteAssignBody(BaseModel):
    score: float = 0
    notes: str = ''


@router.post('/classrooms/assignments/{assignment_id}/complete')
def complete_assignment(assignment_id: int, body: CompleteAssignBody, session: Session = Depends(get_session)):
    a = session.get(Assignment, assignment_id)
    if not a: raise HTTPException(404, 'Assignment not found')
    a.status = 'completed'; a.completed_at = datetime.utcnow(); a.score = body.score
    session.add(a); session.commit(); return {'ok': True}


@router.get('/classrooms/sessions/{session_id}/stream')
def stream(session_id: int):
    def gen():
        yield 'event: hello\ndata: {"ok":true}\n\n'
    return StreamingResponse(gen(), media_type='text/event-stream')


@router.post('/classrooms/sessions/{session_id}/whiteboard/snapshot')
def save_snap(session_id: int, file: UploadFile = File(...)):
    p = whiteboard_path(session_id) / 'snapshot.png'
    p.write_bytes(file.file.read())
    return {'ok': True, 'file': str(p)}


@router.get('/classrooms/sessions/{session_id}/whiteboard/snapshot.png')
def get_snap(session_id: int):
    p = whiteboard_path(session_id) / 'snapshot.png'
    if not p.exists():
        raise HTTPException(404, 'No snapshot')
    return FileResponse(str(p), media_type='image/png')


@router.post('/classrooms/sessions/{session_id}/deck/from_lesson')
def deck_from_lesson(session_id: int, lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson: raise HTTPException(404, 'Lesson not found')
    slides = create_deck_from_text(session_id, lesson.title, lesson.content_md)
    d = SlideDeck(session_id=session_id, title=lesson.title, slides_json=json.dumps(slides))
    session.add(d); session.commit(); session.refresh(d); return d


@router.post('/classrooms/sessions/{session_id}/deck/from_concept')
def deck_from_concept(session_id: int, concept_id: int, session: Session = Depends(get_session)):
    c = session.get(Concept, concept_id)
    if not c: raise HTTPException(404, 'Concept not found')
    slides = create_deck_from_text(session_id, c.title, c.description)
    d = SlideDeck(session_id=session_id, title=c.title, slides_json=json.dumps(slides))
    session.add(d); session.commit(); session.refresh(d); return d


@router.get('/classrooms/sessions/{session_id}/deck/{deck_id}')
def get_deck(session_id: int, deck_id: int, session: Session = Depends(get_session)):
    d = session.get(SlideDeck, deck_id)
    if not d or d.session_id != session_id: raise HTTPException(404, 'Deck not found')
    return {'deck': d, 'slides': json.loads(d.slides_json)}


class PresentBody(BaseModel):
    deck_id: int
    slide_index: int


@router.post('/classrooms/sessions/{session_id}/present')
def present(session_id: int, body: PresentBody, session: Session = Depends(get_session)):
    session.add(ClassroomEvent(session_id=session_id, type='present', payload_json=json.dumps(body.model_dump()))); session.commit()
    return {'ok': True}


class LiveQuizBody(BaseModel):
    title: str = 'Quick check'
    concept_id: int | None = None
    questions_json: list[dict] = []


@router.post('/classrooms/sessions/{session_id}/livequiz/create')
def create_livequiz(session_id: int, body: LiveQuizBody, session: Session = Depends(get_session)):
    questions = body.questions_json or [{"prompt": "What is the key idea?", "answer": "open"}]
    q = LiveQuiz(session_id=session_id, title=body.title, concept_id=body.concept_id, questions_json=json.dumps(questions), status='draft')
    session.add(q); session.commit(); session.refresh(q); return q


@router.post('/classrooms/livequiz/{quiz_id}/open')
def open_quiz(quiz_id: int, session: Session = Depends(get_session)):
    q = session.get(LiveQuiz, quiz_id)
    if not q: raise HTTPException(404, 'Quiz not found')
    q.status='open'; session.add(q); session.commit(); return {'ok': True}


class SubmitQuizBody(BaseModel):
    profile_id: int
    answers: list


@router.post('/classrooms/livequiz/{quiz_id}/submit')
def submit_quiz(quiz_id: int, body: SubmitQuizBody, session: Session = Depends(get_session)):
    q = session.get(LiveQuiz, quiz_id)
    if not q: raise HTTPException(404, 'Quiz not found')
    questions = json.loads(q.questions_json)
    score = min(1.0, len(body.answers) / max(1, len(questions)))
    r = LiveQuizResponse(live_quiz_id=quiz_id, profile_id=body.profile_id, answers_json=json.dumps(body.answers), score=score)
    session.add(r); session.commit(); session.refresh(r)
    cs = session.get(ClassroomSession, q.session_id)
    if q.concept_id and cs:
        update_mastery(session, body.profile_id, cs.course_id, q.concept_id, 'quiz', score, {'live_quiz_id': quiz_id})
    return r


@router.get('/classrooms/livequiz/{quiz_id}/results')
def quiz_results(quiz_id: int, session: Session = Depends(get_session)):
    rows = session.exec(select(LiveQuizResponse).where(LiveQuizResponse.live_quiz_id == quiz_id)).all()
    agg = sum(r.score for r in rows) / max(1, len(rows))
    return {'aggregate_score': agg, 'responses': rows}


class TeachCreateBody(BaseModel):
    concept_id: int


@router.post('/classrooms/sessions/{session_id}/teachback/create')
def teach_create(session_id: int, body: TeachCreateBody, session: Session = Depends(get_session)):
    c = session.get(Concept, body.concept_id)
    if not c: raise HTTPException(404, 'Concept not found')
    rubric = {"correctness": 4, "completeness": 4, "clarity": 4, "example_usage": 4}
    p = TeachbackPrompt(session_id=session_id, concept_id=body.concept_id, prompt=f"Explain {c.title} in your own words.", rubric_json=json.dumps(rubric))
    session.add(p); session.commit(); session.refresh(p); return p


class TeachSubmitBody(BaseModel):
    profile_id: int
    response_text: str


@router.post('/classrooms/teachback/{prompt_id}/submit')
def teach_submit(prompt_id: int, body: TeachSubmitBody, session: Session = Depends(get_session)):
    p = session.get(TeachbackPrompt, prompt_id)
    if not p: raise HTTPException(404, 'Prompt not found')
    concept = session.get(Concept, p.concept_id)
    score = teachback_score(body.response_text, concept.description if concept else p.prompt)
    fb = 'Good attempt. Add one concrete example to improve completeness.' if score['example_usage'] == 0 else 'Nice explanation with an example.'
    s = TeachbackSubmission(prompt_id=prompt_id, profile_id=body.profile_id, response_text=body.response_text, score_json=json.dumps(score), feedback_md=fb)
    session.add(s)
    session.add(ClassroomEvent(session_id=p.session_id, type='teachback_submit', payload_json=json.dumps({'profile_id': body.profile_id, 'prompt_id': prompt_id})))
    session.commit(); session.refresh(s)
    return s


@router.get('/classrooms/teachback/{prompt_id}/results')
def teach_results(prompt_id: int, session: Session = Depends(get_session)):
    return session.exec(select(TeachbackSubmission).where(TeachbackSubmission.prompt_id == prompt_id)).all()


@router.post('/classrooms/teachback/{prompt_id}/apply_mastery')
def teach_apply(prompt_id: int, session: Session = Depends(get_session)):
    p = session.get(TeachbackPrompt, prompt_id)
    if not p: raise HTTPException(404, 'Prompt not found')
    cs = session.get(ClassroomSession, p.session_id)
    subs = session.exec(select(TeachbackSubmission).where(TeachbackSubmission.prompt_id == prompt_id)).all()
    for sub in subs:
        sj = json.loads(sub.score_json)
        score = min(1.0, sum(sj.values()) / 16.0)
        update_mastery(session, sub.profile_id, cs.course_id, p.concept_id, 'exercise', score, {'teachback_prompt_id': prompt_id})
    return {'updated': len(subs)}


@router.get('/classrooms/sessions/{session_id}/summary')
def summary(session_id: int, session: Session = Depends(get_session)):
    return classroom_summary(session, session_id)
