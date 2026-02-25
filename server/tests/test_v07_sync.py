import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app
from app.db import engine
from app.models import EvidenceEvent, MasteryState, Profile
from app.services.sync_crypto import SyncCryptoError, decrypt_json, derive_key, encrypt_json
from app.services.sync_packager import build_sync_zip, parse_sync_zip

client = TestClient(app)


def mk_profile(name):
    return client.post('/api/profiles', json={'display_name': name, 'role': 'adult', 'timezone': 'UTC', 'day_start_time': '06:00'}).json()['id']


def test_sync_crypto_roundtrip():
    payload = {'hello': 'world', 'n': 42}
    salt = b'1234567890123456'
    key = derive_key('pw-1', salt, 1000)
    blob, _, _ = encrypt_json(payload, key, nonce=b'123456789012')
    dec = decrypt_json(blob, key)
    assert dec == payload
    with pytest.raises(SyncCryptoError):
        bad_key = derive_key('wrong', salt, 1000)
        decrypt_json(blob, bad_key)


def test_sync_package_export_import_and_idempotent_merge():
    src = mk_profile('SyncSrc')
    dst = mk_profile('SyncDst')
    with Session(engine) as s:
        s.add(EvidenceEvent(profile_id=src, course_id=1, concept_id=1, kind='quiz', score=0.9, meta_json='{}'))
        s.commit()

    with Session(engine) as s:
        blob = build_sync_zip(s, profile_id=src, scope='learning_record_only', days=30, events=50, passphrase='pw-sync')

    files = {'file': ('demo.growora-sync.zip', blob, 'application/zip')}
    data = {'passphrase': 'pw-sync', 'target_profile_id': str(dst)}
    first = client.post('/api/sync/import', files=files, data=data)
    assert first.status_code == 200
    first_sum = first.json()['summary']
    assert first_sum['imported_events_count'] >= 1

    second = client.post('/api/sync/import', files=files, data=data)
    assert second.status_code == 200
    second_sum = second.json()['summary']
    assert second_sum['imported_events_count'] == 0
    assert second_sum['skipped_duplicates_count'] >= 1


def test_sync_merge_recomputes_mastery():
    src = mk_profile('MasterySrc')
    dst = mk_profile('MasteryDst')
    with Session(engine) as s:
        s.add(EvidenceEvent(profile_id=src, course_id=2, concept_id=10, kind='quiz', score=1.0, meta_json='{}'))
        s.commit()
        blob = build_sync_zip(s, profile_id=src, scope='learning_record_only', days=30, events=50, passphrase='pw-m')

    res = client.post('/api/sync/import', files={'file': ('x.growora-sync.zip', blob, 'application/zip')}, data={'passphrase': 'pw-m', 'target_profile_id': str(dst)})
    assert res.status_code == 200
    assert res.json()['summary']['recomputed_mastery_count'] >= 1

    with Session(engine) as s:
        st = s.exec(select(MasteryState).where(MasteryState.profile_id == dst, MasteryState.course_id == 2, MasteryState.concept_id == 10)).first()
        assert st is not None
        assert st.theta > 0


def test_manifest_validation_tamper_payload_hash():
    pid = mk_profile('TamperSrc')
    with Session(engine) as s:
        blob = build_sync_zip(s, profile_id=pid, scope='learning_record_only', days=30, events=10, passphrase='pw-t')

    manifest, payload = parse_sync_zip(blob)
    manifest['payload_sha256'] = '00' * 32
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest))
        zf.writestr('payload.bin', payload)

    res = client.post('/api/sync/import', files={'file': ('tamper.growora-sync.zip', out.getvalue(), 'application/zip')}, data={'passphrase': 'pw-t'})
    assert res.status_code == 400


def test_lan_pairing_single_use():
    owner = mk_profile('PairHost')
    classroom = client.post('/api/classrooms', json={'name': 'PairClass'}, headers={'X-Growora-Profile': str(owner)}).json()
    room_session = client.post(f'/api/classrooms/{classroom["id"]}/sessions/start', json={'course_id': 1, 'agenda': ['sync'], 'mode': 'live', 'title': 'pair'}, headers={'X-Growora-Profile': str(owner)}).json()
    room = client.post('/api/lan/rooms/create', json={'classroom_id': classroom['id'], 'session_id': room_session['id']}, headers={'X-Growora-Profile': str(owner)}).json()
    code = room['room_code']

    pair = client.post('/api/lan/sync/pairing/create', data={'room_code': code, 'scope': 'learning_record_only', 'days': '30', 'events': '10'})
    assert pair.status_code == 200
    pair_code = pair.json()['pair_code']

    join = client.post(f'/api/lan/rooms/{code}/join', json={'client_name': 'tablet', 'device_type': 'tablet'}).json()
    client.post(f'/api/lan/rooms/{code}/approve', json={'client_id': join['client_id'], 'profile_id': owner, 'permissions': {'view': True}}, headers={'X-Growora-Profile': str(owner)})

    with Session(engine) as s:
        pkg = build_sync_zip(s, profile_id=owner, scope='learning_record_only', days=30, events=10, passphrase='mesh-pass')

    first = client.post('/api/lan/sync/upload', data={'room_code': code, 'pairing_code': pair_code, 'passphrase': 'mesh-pass', 'target_profile_id': str(owner)}, files={'file': ('a.growora-sync.zip', pkg, 'application/zip')}, headers={'Authorization': f'Bearer {join["token"]}'})
    assert first.status_code == 200
    second = client.post('/api/lan/sync/upload', data={'room_code': code, 'pairing_code': pair_code, 'passphrase': 'mesh-pass', 'target_profile_id': str(owner)}, files={'file': ('a.growora-sync.zip', pkg, 'application/zip')}, headers={'Authorization': f'Bearer {join["token"]}'})
    assert second.status_code == 400
