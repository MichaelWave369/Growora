from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_profile_select_tutor_and_backup_smoke():
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['ok'] is True

    created = client.post('/api/profiles', json={
        'display_name': 'ReleaseSmoke',
        'role': 'adult',
        'timezone': 'UTC',
        'day_start_time': '06:00',
    })
    assert created.status_code == 200
    profile_id = created.json()['id']

    listed = client.get('/api/profiles')
    assert listed.status_code == 200
    assert any(p['id'] == profile_id for p in listed.json())

    selected = client.post(f'/api/profiles/{profile_id}/select')
    assert selected.status_code == 200
    assert selected.json()['active_profile_id'] == profile_id

    tutor = client.post(
        '/api/tutor/chat',
        headers={'X-Growora-Profile': str(profile_id)},
        json={'message': 'Give me one study tip', 'privacy_mode': True},
    )
    assert tutor.status_code == 200
    payload = tutor.json()
    assert 'response' in payload and isinstance(payload['response'], str)

    backup = client.post('/api/backup/create', data={'include_exports': 'true'})
    assert backup.status_code == 200
    assert 'file' in backup.json()
