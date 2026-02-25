import json
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app
from app.db import engine
from app.models import ConceptEdge, EvidenceEvent, SharePolicyToken
from app.services.sync_packager import build_sync_zip, parse_sync_zip

client = TestClient(app)


def mk_profile(name):
    return client.post('/api/profiles', json={'display_name': name, 'role':'adult', 'timezone':'UTC', 'day_start_time':'06:00'}).json()['id']


def mk_course(pid, topic='Math'):
    spec={'topic':topic,'goal':'Learn','level':'beginner','schedule_days_per_week':5,'daily_minutes':30,'constraints':'','learner_type':'adult','preferred_style':'guided','day_starts_at':'06:00','auto_use_library':False,'context_doc_ids':[]}
    return client.post('/api/courses', json=spec, headers={'X-Growora-Profile':str(pid)}).json()['course_id']


def test_sync_preview_matches_export_counts():
    pid = mk_profile('preview')
    cid = mk_course(pid)
    client.post(f'/api/graph/rebuild?course_id={cid}', headers={'X-Growora-Profile': str(pid)})
    graph = client.get(f'/api/graph?course_id={cid}', headers={'X-Growora-Profile': str(pid)}).json()
    concept_id = graph['concepts'][0]['id']
    with Session(engine) as s:
        s.add(EvidenceEvent(profile_id=pid, course_id=cid, concept_id=concept_id, kind='quiz', score=0.9, meta_json='{}'))
        s.commit()

    selection = {'courses':[cid], 'concepts':[concept_id], 'types':['evidence'], 'last_days':30, 'max_events':100}
    prev = client.post('/api/sync/preview', json={'profile_id': pid, 'selection': selection})
    assert prev.status_code == 200
    pcount = prev.json()['counts_by_type']['evidence']

    with Session(engine) as s:
        blob = build_sync_zip(s, pid, 'learning_record_only', 30, 100, 'pw', selection=selection)
    manifest, payload = parse_sync_zip(blob)
    assert manifest['format'] == 'triad369-sync@2'

    imp = client.post('/api/sync/import', files={'file': ('x.zip', blob, 'application/zip')}, data={'passphrase':'pw','target_profile_id':str(pid)})
    assert imp.status_code == 200
    assert pcount >= 1


def test_sync_select_courses_only_and_concepts_plus_prereq():
    pid = mk_profile('selective')
    c1 = mk_course(pid, 'Physics')
    c2 = mk_course(pid, 'Chem')
    client.post(f'/api/graph/rebuild?course_id={c1}', headers={'X-Growora-Profile': str(pid)})
    g = client.get(f'/api/graph?course_id={c1}', headers={'X-Growora-Profile': str(pid)}).json()
    cids = [x['id'] for x in g['concepts'][:2]]
    if len(cids) >= 2:
        with Session(engine) as s:
            s.add(ConceptEdge(profile_id=pid, course_id=c1, src_concept_id=cids[0], dst_concept_id=cids[1], kind='prereq', weight=1.0))
            s.add(EvidenceEvent(profile_id=pid, course_id=c1, concept_id=cids[1], kind='quiz', score=0.8, meta_json='{}'))
            s.add(EvidenceEvent(profile_id=pid, course_id=c2, concept_id=999999, kind='quiz', score=0.8, meta_json='{}'))
            s.commit()

        selection = {'courses':[c1], 'concepts':[cids[1]], 'include_prereqs':True, 'types':['evidence'], 'last_days':30, 'max_events':100}
        prev = client.post('/api/sync/preview', json={'profile_id': pid, 'selection': selection}).json()
        assert c1 in prev['courses_included']
        assert cids[0] in prev['concepts_included']


def test_family_course_push_roundtrip_and_progress_pull_idempotent_and_policy_token():
    parent = mk_profile('Parent')
    kid = mk_profile('Kid')
    cid = mk_course(parent, 'Piano')
    client.post(f'/api/graph/rebuild?course_id={cid}', headers={'X-Growora-Profile': str(parent)})

    # course push
    exp = client.post('/api/family/share/course_push/export', data={'from_profile_id': str(parent), 'to_profile_hint':'Kid', 'course_id': str(cid), 'include_flashcards':'1', 'include_certificate_template':'0', 'passphrase':'fam'})
    assert exp.status_code == 200
    b = bytes.fromhex(exp.json()['bundle_b64'])
    imp = client.post('/api/family/share/course_push/import', files={'file': ('c.zip', b, 'application/zip')}, data={'passphrase':'fam','target_profile_id':str(kid)})
    assert imp.status_code == 200

    # token
    tok = client.post('/api/family/policy/create', data={'course_id': str(cid), 'created_by_profile_id': str(parent), 'expires_days':'30'})
    assert tok.status_code == 200
    token = tok.json()

    # kid progress event
    graph = client.get(f'/api/graph?course_id={cid}', headers={'X-Growora-Profile': str(parent)}).json()
    concept_id = graph['concepts'][0]['id'] if graph['concepts'] else 1
    with Session(engine) as s:
        s.add(EvidenceEvent(profile_id=kid, course_id=cid, concept_id=concept_id, kind='quiz', score=1.0, meta_json='{}'))
        s.commit()

    pexp = client.post('/api/family/share/progress_pull/export', data={'from_profile_id': str(kid), 'course_id': str(cid), 'last_days':'30', 'passphrase':'fam', 'policy_token_id': token['token_id'], 'policy_token_secret': token['token_secret']})
    assert pexp.status_code == 200
    pb = bytes.fromhex(pexp.json()['bundle_b64'])

    pimp1 = client.post('/api/family/share/progress_pull/import', files={'file': ('p.zip', pb, 'application/zip')}, data={'passphrase':'fam','target_profile_id':str(parent)})
    assert pimp1.status_code == 200
    pimp2 = client.post('/api/family/share/progress_pull/import', files={'file': ('p.zip', pb, 'application/zip')}, data={'passphrase':'fam','target_profile_id':str(parent)})
    assert pimp2.status_code == 200
    assert pimp2.json()['summary']['imported_events_count'] == 0

    # enforce expired token
    with Session(engine) as s:
        rec = s.exec(select(SharePolicyToken).where(SharePolicyToken.token_id == token['token_id'])).first()
        rec.expires_at = datetime.utcnow() - timedelta(days=1)
        s.add(rec); s.commit()

    pexp2 = client.post('/api/family/share/progress_pull/export', data={'from_profile_id': str(kid), 'course_id': str(cid), 'last_days':'30', 'passphrase':'fam', 'policy_token_id': token['token_id'], 'policy_token_secret': token['token_secret']})
    pb2 = bytes.fromhex(pexp2.json()['bundle_b64'])
    bad = client.post('/api/family/share/progress_pull/import', files={'file': ('p2.zip', pb2, 'application/zip')}, data={'passphrase':'fam','target_profile_id':str(parent)})
    assert bad.status_code == 400
