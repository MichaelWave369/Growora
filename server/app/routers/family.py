import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.auth import require_local_admin
from app.db import get_session
from app.models import SharePolicyToken
from app.services.family_share_importer import import_course_push, import_progress_pull
from app.services.family_share_packager import build_course_push_zip, build_progress_pull_zip, parse_family_share_zip

router = APIRouter(prefix='/api/family', tags=['family'])


@router.post('/share/course_push/export', dependencies=[Depends(require_local_admin)])
def course_push_export(
    from_profile_id: int = Form(...),
    to_profile_hint: str = Form('Learner'),
    course_id: int = Form(...),
    include_flashcards: bool = Form(False),
    include_certificate_template: bool = Form(False),
    passphrase: str = Form(...),
    session: Session = Depends(get_session),
):
    blob = build_course_push_zip(session, from_profile_id, to_profile_hint, course_id, include_flashcards, include_certificate_template, passphrase)
    return {'filename': f'course_push_{course_id}.zip', 'bytes': len(blob), 'bundle_b64': blob.hex()}


@router.post('/share/course_push/import', dependencies=[Depends(require_local_admin)])
def course_push_import(
    file: UploadFile = File(...),
    passphrase: str = Form(...),
    target_profile_id: int = Form(...),
    session: Session = Depends(get_session),
):
    try:
        manifest, ciphertext = parse_family_share_zip(file.file.read())
        return {'ok': True, 'summary': import_course_push(session, manifest, ciphertext, passphrase, target_profile_id)}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post('/share/progress_pull/export', dependencies=[Depends(require_local_admin)])
def progress_pull_export(
    from_profile_id: int = Form(...),
    course_id: int = Form(...),
    last_days: int = Form(30),
    passphrase: str = Form(...),
    policy_token_id: str | None = Form(default=None),
    policy_token_secret: str | None = Form(default=None),
    session: Session = Depends(get_session),
):
    blob = build_progress_pull_zip(session, from_profile_id, course_id, last_days, passphrase, policy_token_id, policy_token_secret)
    return {'filename': f'progress_pull_{course_id}.zip', 'bytes': len(blob), 'bundle_b64': blob.hex()}


@router.post('/share/progress_pull/import', dependencies=[Depends(require_local_admin)])
def progress_pull_import(
    file: UploadFile = File(...),
    passphrase: str = Form(...),
    target_profile_id: int = Form(...),
    session: Session = Depends(get_session),
):
    try:
        manifest, ciphertext = parse_family_share_zip(file.file.read())
        return {'ok': True, 'summary': import_progress_pull(session, manifest, ciphertext, passphrase, target_profile_id)}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post('/policy/create', dependencies=[Depends(require_local_admin)])
def create_policy(course_id: int = Form(...), created_by_profile_id: int = Form(...), expires_days: int = Form(30), session: Session = Depends(get_session)):
    secret = secrets.token_urlsafe(24)
    token_id = secrets.token_hex(8)
    rec = SharePolicyToken(
        course_id=course_id,
        created_by_profile_id=created_by_profile_id,
        mode='progress_only',
        secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
        token_id=token_id,
        expires_at=datetime.utcnow() + timedelta(days=expires_days),
    )
    session.add(rec); session.commit(); session.refresh(rec)
    return {'id': rec.id, 'token_id': token_id, 'token_secret': secret, 'expires_at': rec.expires_at}


@router.post('/policy/revoke', dependencies=[Depends(require_local_admin)])
def revoke_policy(id: int = Form(...), session: Session = Depends(get_session)):
    rec = session.get(SharePolicyToken, id)
    if not rec:
        raise HTTPException(404, 'Policy not found')
    rec.revoked_at = datetime.utcnow()
    session.add(rec); session.commit()
    return {'ok': True}
