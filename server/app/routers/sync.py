import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlmodel import Session, select

from app.core.auth import get_lan_client, require_local_admin
from app.core.config import settings
from app.db import get_session
from app.models import LanRoom, LanSyncPairing, SyncAudit
from app.services.lan import expires_in, hash_token, random_code
from app.services.sync_merge import merge_sync_payload
from app.services.sync_packager import build_sync_zip, parse_sync_zip

router = APIRouter(prefix='/api', tags=['sync'])


@router.post('/sync/export', dependencies=[Depends(require_local_admin)])
def sync_export(
    profile_id: int = Form(...),
    scope: str = Form('learning_record_only'),
    days: int | None = Form(default=None),
    events: int | None = Form(default=None),
    passphrase: str = Form(...),
    session: Session = Depends(get_session),
):
    blob = build_sync_zip(session, profile_id=profile_id, scope=scope, days=days, events=events, passphrase=passphrase)
    audit = SyncAudit(action='export', profile_id=profile_id, device_id='host-local', status='ok', detail_json=json.dumps({'scope': scope, 'bytes': len(blob)}))
    session.add(audit); session.commit()
    headers = {'Content-Disposition': f'attachment; filename="profile_{profile_id}_{datetime.utcnow().date()}.growora-sync.zip"'}
    return Response(content=blob, media_type='application/zip', headers=headers)


@router.post('/sync/import', dependencies=[Depends(require_local_admin)])
def sync_import(
    file: UploadFile = File(...),
    passphrase: str = Form(...),
    target_profile_id: int | None = Form(default=None),
    session: Session = Depends(get_session),
):
    raw = file.file.read()
    max_bytes = settings.growora_sync_max_zip_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(400, f'Sync package too large (max {settings.growora_sync_max_zip_mb} MB)')
    try:
        manifest, ciphertext = parse_sync_zip(raw)
        summary = merge_sync_payload(session, manifest, ciphertext, passphrase, target_profile_id)
        return {'ok': True, 'summary': summary}
    except Exception as exc:
        session.rollback()
        audit = SyncAudit(action='import', profile_id=target_profile_id, device_id='unknown', status='error', detail_json=json.dumps({'error': str(exc)}))
        session.add(audit); session.commit()
        raise HTTPException(400, str(exc))


@router.get('/sync/audit', dependencies=[Depends(require_local_admin)])
def sync_audit(session: Session = Depends(get_session)):
    rows = session.exec(select(SyncAudit).order_by(SyncAudit.ts.desc())).all()
    return rows


@router.post('/lan/sync/pairing/create', dependencies=[Depends(require_local_admin)])
def create_pairing(room_code: str = Form(...), scope: str = Form('learning_record_only'), days: int | None = Form(default=None), events: int | None = Form(default=None), session: Session = Depends(get_session)):
    room = session.exec(select(LanRoom).where(LanRoom.code == room_code)).first()
    if not room:
        raise HTTPException(404, 'Room not found')
    code = random_code(8)
    p = LanSyncPairing(code=code, room_id=room.id, expires_at=datetime.utcnow() + timedelta(minutes=5), scope=scope, range_json=json.dumps({'days': days, 'events': events}))
    session.add(p); session.commit(); session.refresh(p)
    return {'pair_code': p.code, 'qr_url': f'/api/lan/sync/pairing/{p.code}/status', 'expires_at': p.expires_at}


@router.get('/lan/sync/pairing/{code}/status')
def pairing_status(code: str, session: Session = Depends(get_session)):
    p = session.exec(select(LanSyncPairing).where(LanSyncPairing.code == code)).first()
    if not p:
        raise HTTPException(404, 'Pairing not found')
    return {'code': p.code, 'status': p.status, 'expires_at': p.expires_at, 'used_at': p.used_at}


@router.post('/lan/sync/upload')
def lan_sync_upload(
    room_code: str = Form(...),
    pairing_code: str = Form(...),
    passphrase: str = Form(...),
    target_profile_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    client=Depends(get_lan_client),
    session: Session = Depends(get_session),
):
    room = session.exec(select(LanRoom).where(LanRoom.code == room_code)).first()
    if not room:
        raise HTTPException(404, 'Room not found')
    pairing = session.exec(select(LanSyncPairing).where(LanSyncPairing.code == pairing_code, LanSyncPairing.room_id == room.id)).first()
    if not pairing:
        raise HTTPException(404, 'Pairing not found')
    if pairing.status != 'active' or pairing.used_at or pairing.expires_at < datetime.utcnow():
        raise HTTPException(400, 'Pairing already used/expired')

    raw = file.file.read()
    manifest, ciphertext = parse_sync_zip(raw)
    summary = merge_sync_payload(session, manifest, ciphertext, passphrase, target_profile_id or client.profile_id_optional)

    pairing.status = 'used'
    pairing.used_at = datetime.utcnow()
    session.add(pairing); session.commit()
    return {'ok': True, 'summary': summary}
