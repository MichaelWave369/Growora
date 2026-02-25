from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def mk_profile(name='GraphUser'):
    return client.post('/api/profiles', json={'display_name': name, 'role':'adult','timezone':'UTC','day_start_time':'06:00'}).json()['id']


def mk_course(pid):
    spec={'topic':'Guitar','goal':'Play','level':'beginner','schedule_days_per_week':5,'daily_minutes':30,'constraints':'night','learner_type':'adult','preferred_style':'guided','day_starts_at':'18:00','auto_use_library':False,'context_doc_ids':[]}
    return client.post('/api/courses', json=spec, headers={'X-Growora-Profile':str(pid)}).json()['course_id']


def test_graph_rebuild_and_mastery_monotonic():
    pid = mk_profile('gm')
    cid = mk_course(pid)
    rb = client.post(f'/api/graph/rebuild?course_id={cid}', headers={'X-Growora-Profile':str(pid)})
    assert rb.status_code == 200
    g = client.get(f'/api/graph?course_id={cid}', headers={'X-Growora-Profile':str(pid)})
    assert g.status_code == 200
    concepts = g.json()['concepts']
    if concepts:
      c_id = concepts[0]['id']
      t1 = client.post('/api/mastery/evidence', json={'course_id':cid,'concept_id':c_id,'kind':'quiz','score':0.8}, headers={'X-Growora-Profile':str(pid)}).json()['theta']
      t2 = client.post('/api/mastery/evidence', json={'course_id':cid,'concept_id':c_id,'kind':'quiz','score':0.9}, headers={'X-Growora-Profile':str(pid)}).json()['theta']
      assert t2 >= t1
