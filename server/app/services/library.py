import hashlib
import json
from pathlib import Path

from fastapi import UploadFile
try:
    from pypdf import PdfReader
except Exception:  # optional dependency in constrained envs
    PdfReader = None
from sqlmodel import Session

from app.db import engine
from app.models import Document, DocumentChunk

UPLOAD_DIR = Path("server/data/uploads")
EXTRACTED_DIR = Path("server/data/extracted")


def _chunk_text(text: str, chunk_size: int = 700) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)] or [""]


def _extract_text(path: Path, mime: str) -> tuple[list[tuple[int, str]], str | None]:
    try:
        if mime in {"text/plain", "text/markdown"} or path.suffix.lower() in {".txt", ".md"}:
            return [(0, path.read_text(encoding="utf-8", errors="ignore"))], None
        if mime == "application/pdf" or path.suffix.lower() == ".pdf":
            if PdfReader is None:
                return [], "PDF extraction unavailable: pypdf not installed"
            reader = PdfReader(str(path))
            return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)], None
        return [], "Unsupported file type"
    except Exception as exc:
        return [], f"Extraction failed: {exc}"


def _sync_fts(chunk: DocumentChunk):
    with engine.connect() as conn:
        conn.exec_driver_sql(
            "INSERT INTO document_chunks_fts(text, document_id, chunk_id, profile_id) VALUES (?, ?, ?, ?)",
            (chunk.text, chunk.document_id, chunk.id, chunk.profile_id),
        )
        conn.commit()


def save_upload(file: UploadFile, tags: list[str], session: Session, profile_id: int) -> Document:
    data = file.file.read()
    digest = hashlib.sha256(data).hexdigest()
    ext = Path(file.filename or "upload.bin").suffix
    path = UPLOAD_DIR / f"{digest}{ext}"
    path.write_bytes(data)

    doc = Document(profile_id=profile_id, filename=file.filename or path.name, mime=file.content_type or "application/octet-stream", size=len(data), sha256=digest, tags_json=json.dumps(tags))
    session.add(doc); session.commit(); session.refresh(doc)

    pages, err = _extract_text(path, doc.mime)
    if err:
        doc.extraction_error = err
        session.add(doc); session.commit()
        return doc

    extracted_blob, idx = [], 0
    for page, text in pages:
        for c in _chunk_text(text):
            if not c.strip():
                continue
            chunk = DocumentChunk(profile_id=profile_id, document_id=doc.id, idx=idx, text=c, page=page, meta_json=json.dumps({}))
            session.add(chunk); session.commit(); session.refresh(chunk)
            _sync_fts(chunk)
            extracted_blob.append({"page": page, "idx": idx, "text": c})
            idx += 1

    (EXTRACTED_DIR / f"{doc.id}.json").write_text(json.dumps(extracted_blob, indent=2), encoding="utf-8")
    return doc


def search_library(query: str, tags: list[str], profile_id: int, limit: int = 8):
    sql = """
    SELECT f.rowid, f.text, f.document_id, f.chunk_id, bm25(document_chunks_fts) as score
    FROM document_chunks_fts f
    WHERE document_chunks_fts MATCH ? AND f.profile_id = ?
    ORDER BY score
    LIMIT ?
    """
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(sql, (query, profile_id, limit)).all()
    results = []
    with Session(engine) as session:
        for _, text, document_id, chunk_id, score in rows:
            doc = session.get(Document, int(document_id))
            if not doc:
                continue
            dtags = json.loads(doc.tags_json or "[]")
            if tags and not any(t in dtags for t in tags):
                continue
            results.append({"document": doc, "chunk_id": chunk_id, "snippet": text[:220] + ("..." if len(text) > 220 else ""), "score": score})
    return results
