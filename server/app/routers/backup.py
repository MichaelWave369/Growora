from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from sqlmodel import Session

from app.db import get_session
from app.core.auth import require_local_admin
from app.services.backup_restore import create_backup, restore_backup
from app.services.jobs import list_jobs
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix='/api', tags=['backup'])


@router.post('/backup/create', dependencies=[Depends(require_local_admin)])
def backup_create(include_attachments: bool = Form(False), include_exports: bool = Form(True)):
    p = create_backup(include_attachments, include_exports)
    return {'file': str(p)}


@router.post('/backup/restore', dependencies=[Depends(require_local_admin)])
def backup_restore(request: Request, file: UploadFile = File(...), overwrite: bool = Form(False), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    _ = resolve_profile_id(session, x_growora_profile, request)
    path = Path('server/data/exports') / f"restore_{file.filename}"
    path.write_bytes(file.file.read())
    return restore_backup(session, path, overwrite)


@router.get('/jobs')
def jobs(request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    return list_jobs(session, pid)
