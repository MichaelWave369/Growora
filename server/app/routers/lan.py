import asyncio
import json
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_lan_client, require_local_admin
from app.core.config import settings
from app.db import get_session
from app.models import ClassroomEvent, ClassroomSession, LanAuthToken, LanClient, LanRoom, Profile
from app.services.lan import expires_in, hash_token, local_ips, random_code, random_token

router = APIRouter(prefix='/api', tags=['lan'])
ws_rooms: dict[str, set[WebSocket]] = defaultdict(set)
room_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _active_room(session: Session, code: str):
    room = session.exec(select(LanRoom).where(LanRoom.code == code)).first()
    if not room or room.status != 'active' or room.expires_at < datetime.utcnow():
        raise HTTPException(404, 'Room not active')
    return room


class CreateRoomBody(BaseModel):
    classroom_id: int
    session_id: int


@router.post('/lan/rooms/create', dependencies=[Depends(require_local_admin)])
def create_room(body: CreateRoomBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = int(x_growora_profile or request.cookies.get('growora_profile_id') or 1)
    code = random_code(8)
    room = LanRoom(classroom_id=body.classroom_id, session_id=body.session_id, code=code, created_by_profile_id=profile_id, expires_at=expires_in(settings.growora_lan_room_ttl_minutes), status='active')
    session.add(room); session.commit(); session.refresh(room)
    ip = next((i for i in local_ips() if i != '127.0.0.1'), '127.0.0.1')
    join_url = f"http://{ip}:{settings.growora_bind_port}/join/{code}"
    return {'room_code': code, 'join_url': join_url, 'expires_at': room.expires_at}


class JoinBody(BaseModel):
    client_name: str
    device_type: str = 'phone'


@router.post('/lan/rooms/{code}/join')
def join(code: str, body: JoinBody, request: Request, session: Session = Depends(get_session)):
    room = _active_room(session, code)
    clients = session.exec(select(LanClient).where(LanClient.room_id == room.id)).all()
    if len(clients) >= settings.growora_lan_max_clients:
        raise HTTPException(400, 'Room full')
    client = LanClient(room_id=room.id, client_name=body.client_name, device_type=body.device_type, ip=request.client.host if request.client else '', status='pending')
    session.add(client); session.commit(); session.refresh(client)
    token = random_token()
    session.add(LanAuthToken(room_id=room.id, token_hash=hash_token(token), expires_at=room.expires_at, client_id=client.id)); session.commit()
    return {'pending': True, 'client_id': client.id, 'token': token}


class ApproveBody(BaseModel):
    client_id: int
    profile_id: int | None = None
    permissions: dict = {}


@router.post('/lan/rooms/{code}/approve', dependencies=[Depends(require_local_admin)])
def approve(code: str, body: ApproveBody, session: Session = Depends(get_session)):
    room = _active_room(session, code)
    client = session.get(LanClient, body.client_id)
    if not client or client.room_id != room.id:
        raise HTTPException(404, 'Client not found')
    if body.profile_id is None:
        p = Profile(display_name=f"Guest - {client.client_name}", role='adult', timezone='UTC', day_start_time='06:00')
        session.add(p); session.commit(); session.refresh(p)
        client.profile_id_optional = p.id
    else:
        client.profile_id_optional = body.profile_id
    perms = {'view': True, 'draw': True, 'quiz': True, 'teachback': True}
    perms.update(body.permissions or {})
    client.permissions_json = json.dumps(perms)
    client.status = 'approved'
    session.add(client); session.commit()
    return {'ok': True}


class DenyBody(BaseModel):
    client_id: int


@router.post('/lan/rooms/{code}/deny', dependencies=[Depends(require_local_admin)])
def deny(code: str, body: DenyBody, session: Session = Depends(get_session)):
    room = _active_room(session, code)
    c = session.get(LanClient, body.client_id)
    if c and c.room_id == room.id:
        c.status = 'denied'; session.add(c); session.commit()
    return {'ok': True}


@router.post('/lan/rooms/{code}/rotate', dependencies=[Depends(require_local_admin)])
def rotate(code: str, session: Session = Depends(get_session)):
    room = _active_room(session, code)
    room.code = random_code(8)
    room.expires_at = expires_in(settings.growora_lan_room_ttl_minutes)
    session.add(room); session.commit(); session.refresh(room)
    return {'room_code': room.code, 'expires_at': room.expires_at}


@router.get('/lan/rooms/{code}/status')
def status(code: str, session: Session = Depends(get_session)):
    room = _active_room(session, code)
    clients = session.exec(select(LanClient).where(LanClient.room_id == room.id)).all()
    csession = session.get(ClassroomSession, room.session_id)
    return {
        'session_state': {'session_id': room.session_id, 'title': csession.title if csession else 'unknown', 'expires_at': room.expires_at},
        'pending_clients': [c for c in clients if c.status == 'pending'],
        'approved_clients': [c for c in clients if c.status == 'approved'],
    }


@router.get('/lan/rooms/{code}/qr.png')
def qr(code: str):
    # Simple SVG-as-png placeholder to avoid external deps
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 120'><rect width='320' height='120' fill='white'/><text x='10' y='60' font-size='22'>JOIN CODE: {code}</text></svg>"
    return Response(content=svg.encode(), media_type='image/svg+xml')


async def _broadcast(code: str, message: dict):
    data = json.dumps(message)
    dead = []
    for ws in list(ws_rooms.get(code, [])):
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for d in dead:
        ws_rooms[code].discard(d)


@router.websocket('/ws/lan/{room_code}')
async def ws_lan(websocket: WebSocket, room_code: str, token: str, session_id: int | None = None):
    await websocket.accept()
    from app.db import engine
    from sqlmodel import Session as DBSession

    with DBSession(engine) as s:
        room = s.exec(select(LanRoom).where(LanRoom.code == room_code)).first()
        if not room:
            await websocket.send_text(json.dumps({'type':'error','payload':'room_not_found'})); await websocket.close(); return
        tok = s.exec(select(LanAuthToken).where(LanAuthToken.token_hash == hash_token(token), LanAuthToken.room_id == room.id)).first()
        if not tok or tok.expires_at < datetime.utcnow():
            await websocket.send_text(json.dumps({'type':'error','payload':'invalid_token'})); await websocket.close(); return
        client = s.get(LanClient, tok.client_id)
        if not client or client.status != 'approved':
            await websocket.send_text(json.dumps({'type':'error','payload':'not_approved'})); await websocket.close(); return

    ws_rooms[room_code].add(websocket)
    await _broadcast(room_code, {'type': 'presence', 'ts': datetime.utcnow().isoformat(), 'room_code': room_code, 'session_id': session_id, 'payload': {'status':'joined'}})
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            mtype = msg.get('type', '')
            payload = msg.get('payload', {})

            with DBSession(engine) as s:
                room = s.exec(select(LanRoom).where(LanRoom.code == room_code)).first()
                tok = s.exec(select(LanAuthToken).where(LanAuthToken.token_hash == hash_token(token), LanAuthToken.room_id == room.id)).first()
                client = s.get(LanClient, tok.client_id) if tok else None
                if not client or client.status != 'approved':
                    await websocket.send_text(json.dumps({'type':'error','payload':'unauthorized'})); continue
                perms = json.loads(client.permissions_json or '{}')
                if mtype == 'whiteboard_draw' and not perms.get('draw', False):
                    await websocket.send_text(json.dumps({'type':'error','payload':'permission_denied'}));
                    continue
                if mtype in {'livequiz_submit'} and not perms.get('quiz', False):
                    await websocket.send_text(json.dumps({'type':'error','payload':'permission_denied'}));
                    continue
                if mtype in {'teachback_submit'} and not perms.get('teachback', False):
                    await websocket.send_text(json.dumps({'type':'error','payload':'permission_denied'}));
                    continue
                s.add(ClassroomEvent(session_id=room.session_id, type=mtype, payload_json=json.dumps(payload)))
                s.commit()

            envelope = {'type': mtype, 'ts': datetime.utcnow().isoformat(), 'room_code': room_code, 'session_id': session_id, 'payload': payload}
            await _broadcast(room_code, envelope)
    except WebSocketDisconnect:
        ws_rooms[room_code].discard(websocket)
        await _broadcast(room_code, {'type': 'presence', 'ts': datetime.utcnow().isoformat(), 'room_code': room_code, 'session_id': session_id, 'payload': {'status':'left'}})
