import io
import json
import uuid
import zipfile
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models import Course, EvidenceEvent, Profile, SharePolicyToken
from app.services.sync_crypto import b64, derive_key, encrypt_json
from app.services.sync_select import build_selection_data


def _wrap_bundle(bundle_kind: str, payload: dict[str, Any], passphrase: str):
    salt = uuid.uuid4().bytes
    key = derive_key(passphrase, salt, settings.growora_sync_kdf_iterations)
    enc, nonce, payload_sha = encrypt_json(payload, key)
    manifest = {
        'format': 'family-share@1',
        'bundle_kind': bundle_kind,
        'created_at': datetime.utcnow().isoformat(),
        'crypto': {'kdf': 'pbkdf2-hmac-sha256', 'cipher': 'stream+hmac-sha256', 'salt': b64(salt), 'nonce': b64(nonce), 'iterations': settings.growora_sync_kdf_iterations},
        'payload_sha256': payload_sha,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('family_share_manifest.json', json.dumps(manifest, indent=2))
        zf.writestr('payload.bin', enc)
    return buf.getvalue()


def parse_family_share_zip(blob: bytes):
    with zipfile.ZipFile(io.BytesIO(blob), 'r') as zf:
        if 'family_share_manifest.json' not in zf.namelist() or 'payload.bin' not in zf.namelist():
            raise ValueError('Malformed family share package')
        return json.loads(zf.read('family_share_manifest.json').decode('utf-8')), zf.read('payload.bin')


def build_course_push_zip(session: Session, from_profile_id: int, to_profile_hint: str, course_id: int, include_flashcards: bool, include_certificate_template: bool, passphrase: str):
    course = session.get(Course, course_id)
    if not course or course.profile_id != from_profile_id:
        raise ValueError('Course not found for profile')
    payload = {
        'from_profile_id': from_profile_id,
        'to_profile_hint': to_profile_hint,
        'course_push': {
            'course': course.model_dump(mode='json'),
            'recommended_schedule': {'day_start_time': course.day_start_time, 'minutes_per_day': course.minutes_per_day},
            'include_flashcards': include_flashcards,
            'include_certificate_template': include_certificate_template,
        }
    }
    return _wrap_bundle('course_push', payload, passphrase)


def build_progress_pull_zip(session: Session, from_profile_id: int, course_id: int, last_days: int, passphrase: str, token_id: str | None = None, token_secret: str | None = None):
    selection = {'courses': [course_id], 'types': ['evidence', 'flashcards', 'mastery'], 'last_days': last_days, 'max_events': 2000}
    selected = build_selection_data(session, from_profile_id, selection)
    payload = {
        'from_profile_id': from_profile_id,
        'progress_pull': {
            'course_id': course_id,
            'selection': selection,
            'evidence': selected.get('learning_events', []),
            'review_logs': selected.get('review_logs', []),
            'mastery': selected.get('mastery_snapshots', []),
            'policy_token_id': token_id,
            'policy_token_secret': token_secret,
        }
    }
    return _wrap_bundle('progress_pull', payload, passphrase)
