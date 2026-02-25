from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_course():
    spec = {
        'topic': 'Guitar',
        'goal': 'Play songs',
        'level': 'beginner',
        'schedule_days_per_week': 5,
        'daily_minutes': 30,
        'constraints': 'night shift',
        'learner_type': 'adult',
        'preferred_style': 'hands-on',
        'day_starts_at': '18:00',
        'auto_use_library': False,
        'context_doc_ids': []
    }
    cr = client.post('/api/courses', json=spec)
    assert cr.status_code == 200
    return cr.json()['course_id']


def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True


def test_create_course_and_due_cards_and_planner():
    course_id = create_course()
    due = client.get(f'/api/flashcards/due?course_id={course_id}')
    assert due.status_code == 200
    cards = due.json()
    assert len(cards) > 0
    rev = client.post('/api/flashcards/review', json={'flashcard_id': cards[0]['id'], 'rating': 5})
    assert rev.status_code == 200

    today = client.get(f'/api/courses/{course_id}/plan/today')
    assert today.status_code == 200
    assert 'time_budget' in today.json()

    next7 = client.get(f'/api/courses/{course_id}/plan/next7')
    assert next7.status_code == 200
    assert len(next7.json()) == 7


def test_library_upload_and_search_and_tags():
    files = {'file': ('notes.txt', b'guitar chord progression night shift practice', 'text/plain')}
    up = client.post('/api/library/upload?tags=music,night', files=files)
    assert up.status_code == 200
    doc_id = up.json()['id']

    q = client.get('/api/library/search?q=guitar')
    assert q.status_code == 200
    assert len(q.json()) >= 1

    tag = client.post(f'/api/library/docs/{doc_id}/tags', json={'tags': ['custom']})
    assert tag.status_code == 200


def test_export_import_and_certificate_verify():
    course_id = create_course()
    ex = client.post(f'/api/export/triad369/{course_id}')
    assert ex.status_code == 200
    path = ex.json()['file']
    with open(path, 'rb') as f:
        imp = client.post('/api/import/triad369', files={'file': ('pkg.zip', f.read(), 'application/zip')})
    assert imp.status_code == 200

    cert = client.get(f'/api/courses/{course_id}/certificate.html')
    assert cert.status_code == 200
    body = cert.text
    cert_id = int(body.split('ID: ')[1].split('</p>')[0])
    verify = client.get(f'/api/verify/{cert_id}')
    assert verify.status_code == 200


def test_publish_dry_run_logs():
    course_id = create_course()
    pub = client.post(f'/api/publish/coevo/{course_id}?dry_run=1')
    assert pub.status_code in (200, 400)
    logs = client.get('/api/publish/logs')
    assert logs.status_code == 200
