from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def mk_profile(name='P'):
    return client.post('/api/profiles', json={'display_name': name, 'role':'adult','timezone':'UTC','day_start_time':'06:00'}).json()['id']


def mk_course(pid):
    spec={'topic':'Coding','goal':'Build','level':'beginner','schedule_days_per_week':5,'daily_minutes':30,'constraints':'','learner_type':'adult','preferred_style':'guided','day_starts_at':'06:00','auto_use_library':False,'context_doc_ids':[]}
    return client.post('/api/courses', json=spec, headers={'X-Growora-Profile':str(pid)}).json()['course_id']


def test_next_best_drills_and_backup_restore():
    pid = mk_profile('planner')
    cid = mk_course(pid)
    nb = client.get(f'/api/courses/{cid}/plan/next_best', headers={'X-Growora-Profile':str(pid)})
    assert nb.status_code == 200
    files={'file': ('notes.txt', b'loops variables functions', 'text/plain')}
    up = client.post('/api/library/upload?tags=code', files=files, headers={'X-Growora-Profile':str(pid)})
    assert up.status_code == 200
    client.post(f'/api/graph/rebuild?course_id={cid}', headers={'X-Growora-Profile':str(pid)})
    g = client.get(f'/api/graph?course_id={cid}', headers={'X-Growora-Profile':str(pid)}).json()
    if g['concepts']:
        c_id = g['concepts'][0]['id']
        dr = client.post('/api/drills/generate', json={'course_id':cid,'concept_id':c_id,'count':2,'difficulty':'beginner'}, headers={'X-Growora-Profile':str(pid)})
        assert dr.status_code == 200 and len(dr.json()) >= 1
        did = dr.json()[0]['id']
        gd = client.post('/api/drills/grade', json={'drill_id':did,'user_answer':'ok','score':0.9}, headers={'X-Growora-Profile':str(pid)})
        assert gd.status_code == 200
    b = client.post('/api/backup/create', data={'include_attachments':'false','include_exports':'true'})
    assert b.status_code == 200
    path = b.json()['file']
    with open(path,'rb') as f:
        r = client.post('/api/backup/restore', files={'file':('backup.zip', f.read(), 'application/zip')}, headers={'X-Growora-Profile':str(pid)})
    assert r.status_code == 200
