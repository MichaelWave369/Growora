from fastapi import Header, Request
from sqlmodel import Session, select

from app.models import Profile


def resolve_profile_id(session: Session, profile_header: str | None, request: Request | None = None) -> int:
    if profile_header:
        try:
            pid = int(profile_header)
            if session.get(Profile, pid):
                return pid
        except ValueError:
            pass
    if request:
        cookie = request.cookies.get("growora_profile_id")
        if cookie and cookie.isdigit() and session.get(Profile, int(cookie)):
            return int(cookie)
    first = session.exec(select(Profile).order_by(Profile.id)).first()
    if not first:
        first = Profile(display_name="Default Learner", role="adult", timezone="UTC", day_start_time="06:00")
        session.add(first)
        session.commit(); session.refresh(first)
    return first.id


def profile_id_dep(request: Request, session: Session, x_growora_profile: str | None = Header(default=None)) -> int:
    return resolve_profile_id(session, x_growora_profile, request)
