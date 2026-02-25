from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.core.config import settings
from app.db import get_session
from app.models import TutorMessage
from app.services.profile_context import resolve_profile_id
from app.services.tutor_engine import tutor_reply

router = APIRouter(prefix='/api', tags=['tutor'])


class ChatBody(BaseModel):
    message: str
    course_id_optional: int | None = None
    privacy_mode: bool = True


@router.post('/tutor/chat')
def tutor_chat(body: ChatBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    result = tutor_reply(session, profile_id, body.message, body.course_id_optional, settings.growora_llm_provider)
    if not body.privacy_mode:
        session.add(TutorMessage(profile_id=profile_id, course_id=body.course_id_optional, role='user', content=body.message))
        session.add(TutorMessage(profile_id=profile_id, course_id=body.course_id_optional, role='assistant', content=result['response']))
        session.commit()
    return result
