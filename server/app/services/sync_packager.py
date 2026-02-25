import io
import json
import uuid
import zipfile
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.core.config import settings
from sqlmodel import select

from app.models import Course, Device, Profile
from app.services.sync_crypto import b64, derive_key, encrypt_json
from app.services.sync_select import build_selection_data


def build_sync_payload(session: Session, profile_id: int, selection: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = session.get(Profile, profile_id)
    if not profile:
        raise ValueError('Profile not found')
    device_id = 'host-local'
    if not session.get(Device, device_id):
        session.add(Device(id=device_id))
        session.commit()

    selection = selection or {'types': ['evidence', 'mastery', 'flashcards', 'sessions', 'certificates', 'classroom'], 'last_days': settings.growora_sync_default_days, 'max_events': settings.growora_sync_default_events}
    selected = build_selection_data(session, profile_id, selection)
    courses = session.exec(select(Course).where(Course.profile_id == profile_id)).all()
    payload = {
        'device_id': device_id,
        'profile_export': {
            'profile': {'display_name': profile.display_name, 'role': profile.role},
            'courses_summary': [{'id': c.id, 'title': c.title, 'topic': c.topic} for c in courses],
            'learning_events': selected.get('learning_events', []),
            'session_events': selected.get('session_events', []),
            'classroom_events': selected.get('classroom_events', []),
            'mastery_snapshots': selected.get('mastery_snapshots', []),
            'review_logs': selected.get('review_logs', []),
            'certificates': selected.get('certificates', []),
            'selection': selected.get('selection', {}),
            'counts_by_type': selected.get('counts_by_type', {}),
        }
    }
    return payload


def build_sync_zip(session: Session, profile_id: int, scope: str, days: int | None, events: int | None, passphrase: str, selection: dict[str, Any] | None = None) -> bytes:
    if selection is None:
        selection = {'types': ['evidence', 'mastery', 'flashcards', 'sessions', 'certificates', 'classroom'], 'last_days': days, 'max_events': events}
    payload = build_sync_payload(session, profile_id, selection)
    salt = uuid.uuid4().bytes
    key = derive_key(passphrase, salt, settings.growora_sync_kdf_iterations)
    enc, nonce, payload_sha = encrypt_json(payload, key)
    manifest = {
        'format': 'triad369-sync@2',
        'app': 'growora',
        'created_at': datetime.utcnow().isoformat(),
        'exporting_profile_id': str(uuid.uuid5(uuid.NAMESPACE_DNS, f'profile:{profile_id}')),
        'exporting_device_id': payload['device_id'],
        'scope': scope,
        'selection': payload['profile_export'].get('selection', {}),
        'policy': {'direction': selection.get('direction', 'two_way'), 'conflict': 'event_sourced'},
        'privacy': {'include_raw_chat': bool(selection.get('include_raw_chat', False)), 'include_attachments': bool(selection.get('include_attachments', False))},
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
