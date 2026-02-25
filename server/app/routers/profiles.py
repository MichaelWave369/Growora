from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.core.auth import require_local_admin
from app.models import Profile

router = APIRouter(prefix="/api", tags=["profiles"])


class ProfileCreate(BaseModel):
    display_name: str
    role: str = "adult"
    timezone: str = "UTC"
    day_start_time: str = "06:00"


class ProfilePatch(BaseModel):
    display_name: str | None = None
    role: str | None = None
    timezone: str | None = None
    day_start_time: str | None = None


class LockBody(BaseModel):
    pin_hash_optional: str | None = None


@router.get("/profiles")
def list_profiles(session: Session = Depends(get_session)):
    return session.exec(select(Profile).order_by(Profile.id)).all()


@router.post("/profiles", dependencies=[Depends(require_local_admin)])
def create_profile(body: ProfileCreate, session: Session = Depends(get_session)):
    p = Profile(**body.model_dump())
    session.add(p); session.commit(); session.refresh(p)
    return p


@router.patch("/profiles/{profile_id}", dependencies=[Depends(require_local_admin)])
def patch_profile(profile_id: int, body: ProfilePatch, session: Session = Depends(get_session)):
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    session.add(p); session.commit()
    return {"ok": True}


@router.post("/profiles/{profile_id}/select")
def select_profile(profile_id: int, response: Response, session: Session = Depends(get_session)):
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    response.set_cookie("growora_profile_id", str(profile_id), httponly=True, samesite="lax")
    return {"ok": True, "active_profile_id": profile_id}


@router.post("/profiles/{profile_id}/lock", dependencies=[Depends(require_local_admin)])
def lock_profile(profile_id: int, body: LockBody, session: Session = Depends(get_session)):
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    p.pin_hash_optional = body.pin_hash_optional
    session.add(p); session.commit()
    return {"ok": True}
