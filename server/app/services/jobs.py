from sqlmodel import Session, select
from app.models import JobRecord


def enqueue(session: Session, profile_id: int, kind: str, detail: str = ''):
    j = JobRecord(profile_id=profile_id, kind=kind, status='queued', detail=detail)
    session.add(j); session.commit(); session.refresh(j)
    return j


def complete(session: Session, job_id: int, status: str = 'done', detail: str = ''):
    j = session.get(JobRecord, job_id)
    if j:
        j.status = status; j.detail = detail; session.add(j); session.commit()


def list_jobs(session: Session, profile_id: int):
    return session.exec(select(JobRecord).where(JobRecord.profile_id == profile_id).order_by(JobRecord.created_at.desc())).all()
