import io
import json
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Certificate,
    ClassroomEvent,
    Course,
    Device,
    EvidenceEvent,
    MasteryState,
    Profile,
    ReviewLog,
    SessionEvent,
)
from app.services.sync_crypto import b64, derive_key, encrypt_json


def _to_jsonable(model):
    d = model.model_dump()
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def _cutoff(days: int | None):
    if not days:
        return None
    return datetime.utcnow() - timedelta(days=days)


def build_sync_payload(session: Session, profile_id: int, scope: str, days: int | None, events_limit: int | None) -> dict[str, Any]:
    profile = session.get(Profile, profile_id)
    if not profile:
        raise ValueError('Profile not found')
    device_id = 'host-local'
    if not session.get(Device, device_id):
        session.add(Device(id=device_id))
        session.commit()
    cutoff = _cutoff(days)
    events_limit = min(events_limit or settings.growora_sync_default_events, settings.growora_sync_max_events)

    courses = session.exec(select(Course).where(Course.profile_id == profile_id)).all()

    def limited(rows):
        rows = rows if cutoff is None else [r for r in rows if getattr(r, 'ts', getattr(r, 'reviewed_at', datetime.utcnow())) >= cutoff]
        return rows[:events_limit]

    payload = {
        'device_id': device_id,
        'profile_export': {
            'profile': {'display_name': profile.display_name, 'role': profile.role},
            'courses_summary': [{'id': c.id, 'title': c.title, 'topic': c.topic} for c in courses],
            'learning_events': [_to_jsonable(e) for e in limited(session.exec(select(EvidenceEvent).where(EvidenceEvent.profile_id == profile_id).order_by(EvidenceEvent.ts.desc())).all())],
            'session_events': [_to_jsonable(e) for e in limited(session.exec(select(SessionEvent).order_by(SessionEvent.ts.desc())).all())] if scope in {'include_sessions'} else [],
            'classroom_events': [_to_jsonable(e) for e in limited(session.exec(select(ClassroomEvent).order_by(ClassroomEvent.ts.desc())).all())] if scope in {'include_sessions'} else [],
            'mastery_snapshots': [_to_jsonable(m) for m in session.exec(select(MasteryState).where(MasteryState.profile_id == profile_id)).all()],
            'review_logs': [_to_jsonable(r) for r in limited(session.exec(select(ReviewLog).where(ReviewLog.profile_id == profile_id).order_by(ReviewLog.reviewed_at.desc())).all())],
            'certificates': [_to_jsonable(c) for c in session.exec(select(Certificate).where(Certificate.profile_id == profile_id)).all()],
        }
    }
    return payload


def build_sync_zip(session: Session, profile_id: int, scope: str, days: int | None, events: int | None, passphrase: str) -> bytes:
    payload = build_sync_payload(session, profile_id, scope, days, events)
    salt = uuid.uuid4().bytes
    key = derive_key(passphrase, salt, settings.growora_sync_kdf_iterations)
    enc, nonce, payload_sha = encrypt_json(payload, key)
    manifest = {
        'format': 'triad369-sync@1',
        'app': 'growora',
        'created_at': datetime.utcnow().isoformat(),
        'exporting_profile_id': str(uuid.uuid5(uuid.NAMESPACE_DNS, f'profile:{profile_id}')),
        'exporting_device_id': payload['device_id'],
        'scope': scope,
        'crypto': {
            'kdf': 'pbkdf2-hmac-sha256',
            'cipher': 'stream+hmac-sha256',
            'salt': b64(salt),
            'nonce': b64(nonce),
            'iterations': settings.growora_sync_kdf_iterations,
        },
        'payload_sha256': payload_sha,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest, indent=2))
        zf.writestr('payload.bin', enc)
    return buf.getvalue()


def parse_sync_zip(data: bytes) -> tuple[dict[str, Any], bytes]:
    with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
        names = set(zf.namelist())
        if 'manifest.json' not in names or 'payload.bin' not in names:
            raise ValueError('Malformed sync package')
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        payload_bin = zf.read('payload.bin')
    return manifest, payload_bin
