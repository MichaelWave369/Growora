import hashlib
import json
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Certificate,
    ClassroomEvent,
    Concept,
    Device,
    EvidenceEvent,
    MasteryState,
    SyncAudit,
)
from app.services.sync_crypto import SyncCryptoError, derive_key, decrypt_json, unb64


def _json_dt(v):
    if isinstance(v, str) and ('T' in v or '-' in v):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            return datetime.utcnow()
    return v


def _validate_manifest(manifest: dict[str, Any]):
    if manifest.get('format') not in {'triad369-sync@1', 'triad369-sync@2'}:
        raise ValueError('Unsupported sync format')
    crypto = manifest.get('crypto') or {}
    if not crypto.get('salt') or not crypto.get('iterations'):
        raise ValueError('Missing crypto manifest fields')


def _recompute_mastery_for_course(session: Session, profile_id: int, course_id: int):
    existing = session.exec(select(MasteryState).where(MasteryState.profile_id == profile_id, MasteryState.course_id == course_id)).all()
    for st in existing:
        session.delete(st)
    session.commit()
    events = session.exec(select(EvidenceEvent).where(EvidenceEvent.profile_id == profile_id, EvidenceEvent.course_id == course_id)).all()
    grouped: dict[int, list[EvidenceEvent]] = {}
    for e in events:
        grouped.setdefault(e.concept_id, []).append(e)
    recomputed = 0
    for concept_id, rows in grouped.items():
        theta = 0.0
        streak = 0
        last_seen = None
        for r in sorted(rows, key=lambda x: x.ts):
            theta = max(-3.0, min(3.0, theta + (r.score - 0.5) * 0.6))
            streak = streak + 1 if r.score >= 0.7 else 0
            last_seen = r.ts
        st = MasteryState(profile_id=profile_id, course_id=course_id, concept_id=concept_id, theta=theta, sigma=0.8, streak=streak, last_seen_at=last_seen)
        session.add(st)
        recomputed += 1
    session.commit()
    return recomputed


def merge_sync_payload(session: Session, manifest: dict[str, Any], ciphertext: bytes, passphrase: str, target_profile_id: int | None = None):
    _validate_manifest(manifest)
    crypto = manifest['crypto']
    salt = unb64(crypto['salt'])
    key = derive_key(passphrase, salt, int(crypto.get('iterations', settings.growora_sync_kdf_iterations)))
    payload = decrypt_json(ciphertext, key)
    plain_hash = hashlib.sha256(json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
    if plain_hash != manifest.get('payload_sha256'):
        raise ValueError('Payload hash mismatch')

    device_id = payload.get('device_id') or 'unknown'
    if not session.get(Device, device_id):
        session.add(Device(id=device_id))
        session.commit()

    profile_meta = payload.get('profile_export', {}).get('profile', {})
    profile_id = target_profile_id or 1
    target_pid = target_profile_id or profile_id
    imported_source_ids: set[str] = set()
    for e in session.exec(select(EvidenceEvent).where(EvidenceEvent.profile_id == target_pid)).all():
        imported_source_ids.add(e.global_event_id)
        try:
            src = json.loads(e.meta_json or '{}').get('source_global_event_id')
            if src:
                imported_source_ids.add(src)
        except Exception:
            pass
    imported = 0
    skipped = 0
    affected_courses: set[int] = set()

    for raw in payload.get('profile_export', {}).get('learning_events', []):
        geid = raw.get('global_event_id')
        if not geid:
            continue
        if geid in imported_source_ids and target_pid == (target_profile_id or raw.get('profile_id') or profile_id):
            skipped += 1
            continue
        existing = session.exec(select(EvidenceEvent).where(EvidenceEvent.global_event_id == geid)).first()
        if existing:
            if (target_profile_id or raw.get('profile_id') or profile_id) == existing.profile_id:
                skipped += 1
                continue
            base = f"{geid}:p{target_profile_id or raw.get('profile_id') or profile_id}"
            geid = base
            n = 1
            while session.exec(select(EvidenceEvent).where(EvidenceEvent.global_event_id == geid)).first():
                n += 1
                geid = f"{base}:{n}"
        ev = EvidenceEvent(
            global_event_id=geid,
            device_id=raw.get('device_id') or device_id,
            profile_id=target_pid,
            course_id=raw.get('course_id'),
            concept_id=raw.get('concept_id'),
            kind=raw.get('kind', 'quiz'),
            score=float(raw.get('score', 0.0)),
            ts=_json_dt(raw.get('ts')),
            meta_json=json.dumps({'source_global_event_id': raw.get('global_event_id'), 'imported_from_device': device_id, 'original_meta': raw.get('meta_json', '{}')}),
        )
        session.add(ev)
        imported += 1
        imported_source_ids.add(raw.get('global_event_id'))
        affected_courses.add(ev.course_id)

    # optional session/classroom events import as append-only
    for model_name, model_cls, ts_key in [
        ('session_events', SessionEvent, 'ts'),
        ('classroom_events', ClassroomEvent, 'ts'),
    ]:
        for raw in payload.get('profile_export', {}).get(model_name, []):
            geid = raw.get('global_event_id')
            if not geid:
                continue
            if session.exec(select(model_cls).where(model_cls.global_event_id == geid)).first():
                skipped += 1
                continue
            obj = model_cls(
                global_event_id=geid,
                device_id=raw.get('device_id') or device_id,
                session_id=raw.get('session_id'),
                ts=_json_dt(raw.get(ts_key)),
                type=raw.get('type', 'sync_import'),
                payload_json=raw.get('payload_json', '{}'),
            )
            session.add(obj)
            imported += 1

    for cert in payload.get('profile_export', {}).get('certificates', []):
        existing = session.exec(select(Certificate).where(Certificate.profile_id == (target_profile_id or cert.get('profile_id')), Certificate.course_id == cert.get('course_id'))).first()
        if existing:
            skipped += 1
            continue
        session.add(Certificate(profile_id=target_profile_id or cert.get('profile_id'), course_id=cert.get('course_id'), recipient_name=cert.get('recipient_name','Imported'), hours_estimate=int(cert.get('hours_estimate',0))))

    session.commit()

    recomputed = 0
    for c in sorted(affected_courses):
        recomputed += _recompute_mastery_for_course(session, target_pid, c)

    summary = {
        'imported_events_count': imported,
        'skipped_duplicates_count': skipped,
        'affected_courses': sorted(affected_courses),
        'recomputed_mastery_count': recomputed,
        'warnings': [] if imported else ['No new events imported'],
        'source_device_id': device_id,
        'source_profile_name': profile_meta.get('display_name', 'unknown'),
        'selection': manifest.get('selection') or payload.get('profile_export', {}).get('selection', {}),
    }
    audit = SyncAudit(action='import', profile_id=target_pid, device_id=device_id, status='ok', detail_json=json.dumps(summary))
    session.add(audit); session.commit(); session.refresh(audit)
    summary['audit_id'] = audit.id
    return summary


# late imports to avoid circular linters
from app.models import SessionEvent
