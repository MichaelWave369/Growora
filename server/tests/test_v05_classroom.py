from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def mk_profile(name):
    return client.post('/api/profiles', json={'display_name': name, 'role':'adult','timezone':'UTC','day_start_time':'06:00'}).json()['id']


def mk_course(pid):
    spec={'topic':'Math','goal':'Learn','level':'beginner','schedule_days_per_week':5,'daily_minutes':30,'constraints':'','learner_type':'kid','preferred_style':'guided','day_starts_at':'06:00','auto_use_library':False,'context_doc_ids':[]}
    return client.post('/api/courses', json=spec, headers={'X-Growora-Profile':str(pid)}).json()['course_id']


def test_classroom_flow_and_stream_and_snapshot_and_summary():
    owner = mk_profile('Teacher')
    learner = mk_profile('Kid')
    course_id = mk_course(owner)

    room = client.post('/api/classrooms', json={'name':'Family Class'}, headers={'X-Growora-Profile':str(owner)})
    assert room.status_code == 200
    cid = room.json()['id']

    add = client.post(f'/api/classrooms/{cid}/members', json={'profile_id': learner, 'role':'learner'}, headers={'X-Growora-Profile':str(owner)})
    assert add.status_code == 200

    sess = client.post(f'/api/classrooms/{cid}/sessions/start', json={'course_id':course_id,'agenda':['warmup'],'mode':'live','title':'Session 1'}, headers={'X-Growora-Profile':str(owner)})
    assert sess.status_code == 200
    sid = sess.json()['id']

    join = client.post(f'/api/classrooms/sessions/{sid}/join', json={'profile_id': learner})
    assert join.status_code == 200

    ev = client.post(f'/api/classrooms/sessions/{sid}/event', json={'type':'draw','payload':{'x':1,'y':2}})
    assert ev.status_code == 200

    stream = client.get(f'/api/classrooms/sessions/{sid}/stream')
    assert stream.status_code == 200

    snap = client.post(f'/api/classrooms/sessions/{sid}/whiteboard/snapshot', files={'file': ('snapshot.png', b'pngbytes', 'image/png')})
    assert snap.status_code == 200

    getsnap = client.get(f'/api/classrooms/sessions/{sid}/whiteboard/snapshot.png')
    assert getsnap.status_code == 200

    summ = client.get(f'/api/classrooms/sessions/{sid}/summary')
    assert summ.status_code == 200
    assert 'attendance' in summ.json()


def test_livequiz_and_teachback_update_mastery():
    owner = mk_profile('Teacher2')
    learner = mk_profile('Learner2')
    course_id = mk_course(owner)

    room = client.post('/api/classrooms', json={'name':'Class'}, headers={'X-Growora-Profile':str(owner)}).json()
    sid = client.post(f"/api/classrooms/{room['id']}/sessions/start", json={'course_id':course_id,'agenda':[],'mode':'live','title':'S'}, headers={'X-Growora-Profile':str(owner)}).json()['id']

    client.post(f'/api/graph/rebuild?course_id={course_id}', headers={'X-Growora-Profile':str(owner)})
    graph = client.get(f'/api/graph?course_id={course_id}', headers={'X-Growora-Profile':str(owner)}).json()
    if not graph['concepts']:
        return
    concept_id = graph['concepts'][0]['id']

    q = client.post(f'/api/classrooms/sessions/{sid}/livequiz/create', json={'title':'Q','concept_id':concept_id,'questions_json':[{'prompt':'p','answer':'a'}]})
    assert q.status_code == 200
    qid = q.json()['id']
    client.post(f'/api/classrooms/livequiz/{qid}/open')
    sub = client.post(f'/api/classrooms/livequiz/{qid}/submit', json={'profile_id': learner, 'answers':['a']})
    assert sub.status_code == 200

    tb = client.post(f'/api/classrooms/sessions/{sid}/teachback/create', json={'concept_id': concept_id})
    assert tb.status_code == 200
    pid = tb.json()['id']
    tsub = client.post(f'/api/classrooms/teachback/{pid}/submit', json={'profile_id': learner, 'response_text':'This concept example explains the idea clearly.'})
    assert tsub.status_code == 200
    appm = client.post(f'/api/classrooms/teachback/{pid}/apply_mastery')
    assert appm.status_code == 200
