import json
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.core.auth import require_local_admin
from app.models import Document, DocumentChunk
from app.services.library import save_upload, search_library
from app.services.profile_context import resolve_profile_id

router = APIRouter(prefix="/api", tags=["library"])


class TagRequest(BaseModel):
    tags: list[str]


@router.post('/library/upload')
def upload(request: Request, tags: str = "", file: UploadFile = File(...), session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    return save_upload(file, tag_list, session, profile_id)


@router.get('/library/docs')
def docs(request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    return session.exec(select(Document).where(Document.profile_id == profile_id)).all()


@router.post('/library/docs/{doc_id}/tags')
def set_tags(doc_id: int, req: TagRequest, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    doc = session.get(Document, doc_id)
    if not doc or doc.profile_id != profile_id:
        raise HTTPException(404, 'Document not found')
    doc.tags_json = json.dumps(req.tags)
    session.add(doc); session.commit()
    return {'ok': True}


@router.delete('/library/docs/{doc_id}', dependencies=[Depends(require_local_admin)])
def delete_doc(doc_id: int, request: Request, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    doc = session.get(Document, doc_id)
    if not doc or doc.profile_id != profile_id:
        raise HTTPException(404, 'Document not found')
    chunks = session.exec(select(DocumentChunk).where(DocumentChunk.document_id == doc_id, DocumentChunk.profile_id == profile_id)).all()
    for c in chunks:
        session.delete(c)
    session.delete(doc)
    session.commit()
    return {'ok': True}


@router.get('/library/search')
def search(request: Request, q: str = Query(...), tags: str = "", course_id: int | None = None, session: Session = Depends(get_session), x_growora_profile: str | None = Header(default=None)):
    _ = course_id
    profile_id = resolve_profile_id(session, x_growora_profile, request)
    return search_library(q, [t.strip() for t in tags.split(',') if t.strip()], profile_id)
