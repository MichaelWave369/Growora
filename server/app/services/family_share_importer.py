import hashlib
import json
from datetime import datetime

from sqlmodel import Session, select

from app.models import Course, EvidenceEvent, MasteryState, SharePolicyToken, SyncAudit
from app.services.mastery import update_mastery
from app.services.sync_crypto import derive_key, decrypt_json, unb64


def _decrypt_bundle(manifest: dict, ciphertext: bytes, passphrase: str):
    crypto = manifest.get('crypto') or {}
    if manifest.get('format') != 'family-share@1':
        raise ValueError('Unsupported family bundle format')
    key = derive_key(passphrase, unb64(crypto['salt']), int(crypto['iterations']))
    payload = decrypt_json(ciphertext, key)
    digest = hashlib.sha256(json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
    if digest != manifest.get('payload_sha256'):
        raise ValueError('Payload hash mismatch')
    return payload


def import_course_push(session: Session, manifest: dict, ciphertext: bytes, passphrase: str, target_profile_id: int):
    payload = _decrypt_bundle(manifest, ciphertext, passphrase)
    course = payload.get('course_push', {}).get('course')
    if not course:
        raise ValueError('Missing course payload')
    c = Course(
        profile_id=target_profile_id,
        title=course.get('title', 'Shared Course'),
        topic=course.get('topic', 'shared'),
        learner_profile_json=course.get('learner_profile_json', '{}'),
        day_start_time=course.get('day_start_time', '06:00'),
        days_per_week=course.get('days_per_week', 5),
        minutes_per_day=course.get('minutes_per_day', 30),
        difficulty=course.get('difficulty', 'beginner'),
        auto_use_library=bool(course.get('auto_use_library', False)),
        context_doc_ids_json='[]',
    )
    session.add(c); session.commit(); session.refresh(c)
    summary = {'created_course_id': c.id, 'title': c.title, 'kind': 'course_push'}
    session.add(SyncAudit(action='import', profile_id=target_profile_id, device_id='family-share', status='ok', detail_json=json.dumps(summary))); session.commit()
    return summary


def import_progress_pull(session: Session, manifest: dict, ciphertext: bytes, passphrase: str, target_profile_id: int):
    payload = _decrypt_bundle(manifest, ciphertext, passphrase)
    data = payload.get('progress_pull', {})
    course_id = data.get('course_id')

    token_id = data.get('policy_token_id')
    token_secret = data.get('policy_token_secret')
    if token_id:
        token = session.exec(select(SharePolicyToken).where(SharePolicyToken.token_id == token_id)).first()
        if not token or token.revoked_at or token.expires_at < datetime.utcnow() or token.mode != 'progress_only':
            raise ValueError('Share policy token invalid/expired/revoked')
        if not token_secret or hashlib.sha256(token_secret.encode()).hexdigest() != token.secret_hash:
            raise ValueError('Share policy secret invalid')
        if token.course_id != course_id:
            raise ValueError('Token course mismatch')

    imported = 0
    skipped = 0
    imported_sources: set[str] = set()
    for row in session.exec(select(EvidenceEvent).where(EvidenceEvent.profile_id == target_profile_id)).all():
        try:
            imported_sources.add(json.loads(row.meta_json or '{}').get('source_global_event_id'))
        except Exception:
            pass
    for e in data.get('evidence', []):
        geid_src = e.get('global_event_id')
        if not geid_src:
            continue
        if geid_src in imported_sources:
            skipped += 1
            continue
        geid = geid_src
        exists_global = session.exec(select(EvidenceEvent).where(EvidenceEvent.global_event_id == geid)).first()
        if exists_global:
            base = f"{geid}:family:{target_profile_id}"; geid = base; n = 1
            while session.exec(select(EvidenceEvent).where(EvidenceEvent.global_event_id == geid)).first():
                n += 1
                geid = f"{base}:{n}"
        session.add(EvidenceEvent(
            global_event_id=geid,
            device_id=e.get('device_id', 'family-share'),
            profile_id=target_profile_id,
            course_id=course_id,
            concept_id=e.get('concept_id'),
            kind=e.get('kind', 'quiz'),
            score=float(e.get('score', 0.0)),
            ts=datetime.fromisoformat(e['ts']) if isinstance(e.get('ts'), str) else datetime.utcnow(),
            meta_json=json.dumps({'family_share': True, 'source_global_event_id': geid_src}),
        ))
        imported += 1
        imported_sources.add(geid_src)
    session.commit()

    # deterministic mastery recompute-by-update
    for e in data.get('evidence', []):
        if e.get('global_event_id'):
            update_mastery(session, target_profile_id, course_id, e.get('concept_id'), e.get('kind', 'quiz'), float(e.get('score', 0.0)), {'family_share': True})

    summary = {'kind': 'progress_pull', 'course_id': course_id, 'imported_events_count': imported, 'skipped_duplicates_count': skipped}
    session.add(SyncAudit(action='import', profile_id=target_profile_id, device_id='family-share', status='ok', detail_json=json.dumps(summary))); session.commit()
    return summary
