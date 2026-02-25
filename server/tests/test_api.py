from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_profile(name: str):
    r = client.post('/api/profiles', json={'display_name': name, 'role': 'adult', 'timezone': 'UTC', 'day_start_time': '06:00'})
    assert r.status_code == 200
    return r.json()['id']


def create_course(profile_id: int):
    spec = {
        'topic': 'Guitar', 'goal': 'Play songs', 'level': 'beginner', 'schedule_days_per_week': 5,
        'daily_minutes': 30, 'constraints': 'night shift', 'learner_type': 'adult',
        'preferred_style': 'hands-on', 'day_starts_at': '18:00', 'auto_use_library': False, 'context_doc_ids': []
    }
    r = client.post('/api/courses', json=spec, headers={'X-Growora-Profile': str(profile_id)})
    assert r.status_code == 200
    return r.json()['course_id']


def test_health_and_profiles_isolation():
    assert client.get('/api/health').status_code == 200
    p1, p2 = create_profile('P1'), create_profile('P2')
    c1 = create_course(p1)
    assert client.get('/api/courses', headers={'X-Growora-Profile': str(p1)}).status_code == 200
    list2 = client.get('/api/courses', headers={'X-Growora-Profile': str(p2)}).json()
    assert all(c['id'] != c1 for c in list2)


def test_session_lifecycle_and_analytics_and_streak():
    pid = create_profile('SessionUser')
    cid = create_course(pid)
    s = client.post('/api/sessions/start', json={'course_id': cid, 'planned_minutes': 9, 'mode': '369'}, headers={'X-Growora-Profile': str(pid)})
    assert s.status_code == 200
    sid = s.json()['id']
    assert client.post('/api/sessions/event', json={'session_id': sid, 'type': 'quiz_wrong', 'payload': {}}, headers={'X-Growora-Profile': str(pid)}).status_code == 200
    assert client.post('/api/sessions/end', json={'session_id': sid, 'notes_md': 'done'}, headers={'X-Growora-Profile': str(pid)}).status_code == 200
    assert client.get(f'/api/sessions/{sid}', headers={'X-Growora-Profile': str(pid)}).status_code == 200
    a = client.get(f'/api/dashboard/analytics?course_id={cid}', headers={'X-Growora-Profile': str(pid)})
    assert a.status_code == 200 and 'weekly_minutes' in a.json()
    st = client.get(f'/api/streak?course_id={cid}', headers={'X-Growora-Profile': str(pid)})
    assert st.status_code == 200 and 'best_streak' in st.json()


def test_library_forge_apply_and_due_cards():
    pid = create_profile('ForgeUser')
    cid = create_course(pid)
    files = {'file': ('notes.txt', b'guitar chord progression practice routine', 'text/plain')}
    up = client.post('/api/library/upload?tags=music', files=files, headers={'X-Growora-Profile': str(pid)})
    assert up.status_code == 200
    doc_id = up.json()['id']
    fr = client.post('/api/forge/run', json={'type': 'flashcards', 'doc_ids': [doc_id], 'count': 5, 'focus_topics': []}, headers={'X-Growora-Profile': str(pid)})
    assert fr.status_code == 200
    job_id = fr.json()['id']
    ap = client.post(f'/api/forge/jobs/{job_id}/apply_to_course', json={'course_id': cid}, headers={'X-Growora-Profile': str(pid)})
    assert ap.status_code == 200
    due = client.get(f'/api/flashcards/due?course_id={cid}', headers={'X-Growora-Profile': str(pid)})
    assert due.status_code == 200 and len(due.json()) > 0


def test_tutor_fallback_and_export_import():
    pid = create_profile('TutorUser')
    cid = create_course(pid)
    chat = client.post('/api/tutor/chat', json={'message': 'help me practice', 'course_id_optional': cid, 'privacy_mode': True}, headers={'X-Growora-Profile': str(pid)})
    assert chat.status_code == 200 and 'citations' in chat.json()
    ex = client.post(f'/api/export/triad369/{cid}', headers={'X-Growora-Profile': str(pid)})
    assert ex.status_code == 200
