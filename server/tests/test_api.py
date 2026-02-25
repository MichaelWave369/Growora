from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True


def test_create_course_and_due_cards():
    spec = {
        'topic': 'Guitar',
        'goal': 'Play songs',
        'level': 'beginner',
        'schedule_days_per_week': 5,
        'daily_minutes': 30,
        'constraints': 'night shift',
        'learner_type': 'adult',
        'preferred_style': 'hands-on',
        'day_starts_at': '18:00'
    }
    cr = client.post('/api/courses', json=spec)
    assert cr.status_code == 200
    course_id = cr.json()['course_id']

    due = client.get(f'/api/flashcards/due?course_id={course_id}')
    assert due.status_code == 200
    cards = due.json()
    assert len(cards) > 0

    rev = client.post('/api/flashcards/review', json={'flashcard_id': cards[0]['id'], 'rating': 5})
    assert rev.status_code == 200
