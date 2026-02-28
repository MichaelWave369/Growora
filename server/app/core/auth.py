import hashlib
from datetime import datetime
from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import LanAuthToken, LanClient


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_local_admin(authorization: str | None = Header(default=None)):
    # LAN tokens are never considered local admin
    if authorization and authorization.lower().startswith("bearer "):
        raise HTTPException(403, "Local-only endpoint")
    return True


def get_lan_client(request: Request, session: Session = Depends(get_session), authorization: str | None = Header(default=None)) -> LanClient:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing LAN token")
    token = authorization.split(" ", 1)[1]
    tok = session.exec(select(LanAuthToken).where(LanAuthToken.token_hash == _hash_token(token))).first()
    if not tok or tok.expires_at < datetime.utcnow():
        raise HTTPException(401, "Invalid/expired token")
    client = session.get(LanClient, tok.client_id)
    if not client or client.status != "approved":
        raise HTTPException(403, "Client not approved")
    client.last_seen_at = datetime.utcnow()
    session.add(client); session.commit()
    return client


def require_lan_permission(perm: str):
    def _inner(client: LanClient = Depends(get_lan_client)):
        import json
        perms = json.loads(client.permissions_json or "{}")
        if not perms.get(perm, False):
            raise HTTPException(403, f"Missing permission: {perm}")
        return client
    return _inner
