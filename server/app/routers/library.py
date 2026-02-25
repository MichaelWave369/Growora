import json
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Document, DocumentChunk
from app.services.library import save_upload, search_library

router = APIRouter(prefix="/api", tags=["library"])


class TagRequest(BaseModel):
    tags: list[str]


@router.post('/library/upload')
def upload(tags: str = "", file: UploadFile = File(...), session: Session = Depends(get_session)):
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    doc = save_upload(file, tag_list, session)
    return doc


@router.get('/library/docs')
def docs(session: Session = Depends(get_session)):
    return session.exec(select(Document)).all()


@router.post('/library/docs/{doc_id}/tags')
def set_tags(doc_id: int, req: TagRequest, session: Session = Depends(get_session)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, 'Document not found')
    doc.tags_json = json.dumps(req.tags)
    session.add(doc); session.commit()
    return {'ok': True}


@router.delete('/library/docs/{doc_id}')
def delete_doc(doc_id: int, session: Session = Depends(get_session)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, 'Document not found')
    chunks = session.exec(select(DocumentChunk).where(DocumentChunk.document_id == doc_id)).all()
    for c in chunks:
        session.delete(c)
    session.delete(doc)
    session.commit()
    return {'ok': True}


@router.get('/library/search')
def search(q: str = Query(...), tags: str = "", course_id: int | None = None):
    _ = course_id
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    return search_library(q, tag_list)
