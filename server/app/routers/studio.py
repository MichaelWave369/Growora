from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.core.auth import require_local_admin
from app.models import Lesson
from app.services.profile_context import resolve_profile_id
from app.services.studio import create_draft_course, generate_lessons, import_markdown, import_pdf_outline

router = APIRouter(prefix='/api', tags=['studio'])


class DraftBody(BaseModel):
    title: str
    topic: str
    template: str | None = None


@router.post('/studio/course', dependencies=[Depends(require_local_admin)])
def create_course(body: DraftBody, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    return create_draft_course(session, pid, body.title, body.topic, body.template)


class LessonGenBody(BaseModel):
    lesson_ids: list[int]


@router.post('/studio/lesson/generate', dependencies=[Depends(require_local_admin)])
def gen_lesson(body: LessonGenBody, session: Session = Depends(get_session)):
    generate_lessons(session, body.lesson_ids)
    return {'ok': True}


@router.post('/studio/import/markdown', dependencies=[Depends(require_local_admin)])
def imp_md(request: Request, title: str = Form(...), markdown_text: str = Form(...), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    c = import_markdown(session, pid, title, markdown_text)
    return {'course_id': c.id}


@router.post('/studio/import/pdf_outline', dependencies=[Depends(require_local_admin)])
def imp_pdf(request: Request, title: str = Form(...), file: UploadFile = File(...), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    pid = resolve_profile_id(session, x_growora_profile, request)
    path = Path('server/data/uploads') / f"studio_{file.filename}"
    path.write_bytes(file.file.read())
    c = import_pdf_outline(session, pid, title, path)
    return {'course_id': c.id}
