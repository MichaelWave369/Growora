import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Course, ForgeJob
from app.services.forge import apply_forge_to_course, run_forge
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix="/api", tags=["forge"])


class ForgeRunBody(BaseModel):
    type: str
    doc_ids: list[int]
    course_id_optional: int | None = None
    difficulty: str = "beginner"
    count: int = 8
    focus_topics: list[str] = []


@router.post('/forge/run')
def forge_run(body: ForgeRunBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    params = body.model_dump(); params.pop('type', None); params.pop('doc_ids', None)
    return run_forge(session, profile_id, body.type, body.doc_ids, params)


@router.get('/forge/jobs')
def list_jobs(request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    return session.exec(select(ForgeJob).where(ForgeJob.profile_id == profile_id).order_by(ForgeJob.created_at.desc())).all()


@router.get('/forge/jobs/{job_id}')
def get_job(job_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    job = session.get(ForgeJob, job_id)
    if not job or job.profile_id != profile_id: raise HTTPException(404, 'Job not found')
    return {'job': job, 'result': json.loads(job.result_ref_json or '{}')}


class ApplyBody(BaseModel):
    course_id: int


@router.post('/forge/jobs/{job_id}/apply_to_course')
def apply_job(job_id: int, body: ApplyBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    job = session.get(ForgeJob, job_id)
    if not job or job.profile_id != profile_id: raise HTTPException(404, 'Job not found')
    c = session.get(Course, body.course_id)
    if not c or c.profile_id != profile_id: raise HTTPException(404, 'Course not found')
    return apply_forge_to_course(session, profile_id, job, body.course_id)
