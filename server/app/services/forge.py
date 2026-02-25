import json
from sqlmodel import Session, select

from app.models import DocumentChunk, Flashcard, ForgeJob


def run_forge(session: Session, profile_id: int, job_type: str, doc_ids: list[int], params: dict):
    chunks = session.exec(
        select(DocumentChunk).where(DocumentChunk.profile_id == profile_id, DocumentChunk.document_id.in_(doc_ids)).limit(12)
    ).all()
    text = "\n".join(c.text[:240] for c in chunks)
    if job_type == "flashcards":
        cards = [{"front": f"Key point {i+1}?", "back": part[:140]} for i, part in enumerate(text.split("\n")[:8]) if part.strip()]
        result = {"flashcards": cards}
    elif job_type == "quiz":
        result = {"questions": [{"type": "short", "prompt": f"Explain: {part[:60]}", "answer": "Open-ended"} for part in text.split("\n")[:6] if part.strip()]}
    elif job_type == "worksheet":
        result = {"markdown": f"# Worksheet\n\n## Source key points\n{text[:1200]}\n\n## Practice prompts\n- Summarize main idea\n- Apply one concept"}
    else:
        result = {"summary": text[:1000]}

    job = ForgeJob(
        profile_id=profile_id,
        status="done",
        type=job_type,
        input_doc_ids_json=json.dumps(doc_ids),
        params_json=json.dumps(params),
        result_ref_json=json.dumps(result),
    )
    session.add(job); session.commit(); session.refresh(job)
    return job


def apply_forge_to_course(session: Session, profile_id: int, job: ForgeJob, course_id: int):
    data = json.loads(job.result_ref_json or "{}")
    added = 0
    for c in data.get("flashcards", []):
        session.add(Flashcard(profile_id=profile_id, course_id=course_id, front=c.get("front", "Q"), back=c.get("back", "A"), tags_json="[]"))
        added += 1
    session.commit()
    return {"added_flashcards": added}
