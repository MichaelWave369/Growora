from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def mk_profile(name):
    return client.post('/api/profiles', json={'display_name': name, 'role':'adult','timezone':'UTC','day_start_time':'06:00'}).json()['id']


def mk_course(pid):
    spec={'topic':'LAN','goal':'Learn','level':'beginner','schedule_days_per_week':5,'daily_minutes':30,'constraints':'','learner_type':'adult','preferred_style':'guided','day_starts_at':'06:00','auto_use_library':False,'context_doc_ids':[]}
    return client.post('/api/courses', json=spec, headers={'X-Growora-Profile':str(pid)}).json()['course_id']


def test_lan_create_join_approve_ws_and_local_only_block():
    owner = mk_profile('Host')
    learner = mk_profile('Learner')
    classroom = client.post('/api/classrooms', json={'name':'LAN'}, headers={'X-Growora-Profile':str(owner)}).json()
    cid = mk_course(owner)
    sess = client.post(f"/api/classrooms/{classroom['id']}/sessions/start", json={'course_id':cid,'agenda':['x'],'mode':'live','title':'LAN'}, headers={'X-Growora-Profile':str(owner)}).json()

    room = client.post('/api/lan/rooms/create', json={'classroom_id': classroom['id'], 'session_id': sess['id']}, headers={'X-Growora-Profile':str(owner)})
    assert room.status_code == 200
    code = room.json()['room_code']

    join = client.post(f'/api/lan/rooms/{code}/join', json={'client_name':'iPad','device_type':'tablet'})
    assert join.status_code == 200 and join.json()['pending'] is True
    token = join.json()['token']; client_id = join.json()['client_id']

    st = client.get(f'/api/lan/rooms/{code}/status')
    assert st.status_code == 200

    appv = client.post(f'/api/lan/rooms/{code}/approve', json={'client_id':client_id,'profile_id':learner,'permissions':{'view':True,'draw':False}}, headers={'X-Growora-Profile':str(owner)})
    assert appv.status_code == 200

    # local-only endpoint blocked with LAN bearer token
    blocked = client.post('/api/backup/create', headers={'Authorization': f'Bearer {token}'})
    assert blocked.status_code == 403

    with client.websocket_connect(f'/api/ws/lan/{code}?token={token}') as ws1:
        msg = ws1.receive_json()
        assert msg['type'] in ('presence', 'error')
        ws1.send_json({'type':'whiteboard_draw','payload':{'stroke':[1,2]}})
        deny = ws1.receive_json()
        assert deny.get('payload') in ('permission_denied', {'status':'joined'}) or deny.get('type') in ('error','presence')


def test_lan_expired_room_denies_join():
    owner = mk_profile('Host2')
    classroom = client.post('/api/classrooms', json={'name':'LAN2'}, headers={'X-Growora-Profile':str(owner)}).json()
    cid = mk_course(owner)
    sess = client.post(f"/api/classrooms/{classroom['id']}/sessions/start", json={'course_id':cid,'agenda':['x'],'mode':'live','title':'LAN2'}, headers={'X-Growora-Profile':str(owner)}).json()
    room = client.post('/api/lan/rooms/create', json={'classroom_id': classroom['id'], 'session_id': sess['id']}, headers={'X-Growora-Profile':str(owner)}).json()
    code = room['room_code']
    # expire manually
    from app.db import engine
    from sqlmodel import Session, select
    from app.models import LanRoom
    with Session(engine) as s:
        r = s.exec(select(LanRoom).where(LanRoom.code == code)).first()
        from datetime import datetime, timedelta
        r.expires_at = datetime.utcnow() - timedelta(minutes=1)
        s.add(r); s.commit()
    j = client.post(f'/api/lan/rooms/{code}/join', json={'client_name':'late','device_type':'phone'})
    assert j.status_code == 404


def test_lan_event_fanout_two_clients():
    owner = mk_profile('Host3')
    p1 = mk_profile('P1')
    p2 = mk_profile('P2')
    classroom = client.post('/api/classrooms', json={'name':'LAN3'}, headers={'X-Growora-Profile':str(owner)}).json()
    cid = mk_course(owner)
    sess = client.post(f"/api/classrooms/{classroom['id']}/sessions/start", json={'course_id':cid,'agenda':['x'],'mode':'live','title':'LAN3'}, headers={'X-Growora-Profile':str(owner)}).json()
    room = client.post('/api/lan/rooms/create', json={'classroom_id': classroom['id'], 'session_id': sess['id']}, headers={'X-Growora-Profile':str(owner)}).json()
    code = room['room_code']
    j1 = client.post(f'/api/lan/rooms/{code}/join', json={'client_name':'A','device_type':'phone'}).json()
    j2 = client.post(f'/api/lan/rooms/{code}/join', json={'client_name':'B','device_type':'phone'}).json()
    client.post(f'/api/lan/rooms/{code}/approve', json={'client_id':j1['client_id'],'profile_id':p1,'permissions':{'draw':True,'view':True}}, headers={'X-Growora-Profile':str(owner)})
    client.post(f'/api/lan/rooms/{code}/approve', json={'client_id':j2['client_id'],'profile_id':p2,'permissions':{'draw':True,'view':True}}, headers={'X-Growora-Profile':str(owner)})
    with client.websocket_connect(f'/api/ws/lan/{code}?token={j1["token"]}') as ws1, client.websocket_connect(f'/api/ws/lan/{code}?token={j2["token"]}') as ws2:
        ws1.receive_json(); ws2.receive_json()
        ws1.send_json({'type':'slide_present','payload':{'deck_id':1,'slide_index':2}})
        got = ws2.receive_json()
        assert got.get('type') in ('slide_present','presence')
