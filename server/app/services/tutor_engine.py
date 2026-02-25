import json
from sqlmodel import Session, select

from app.models import DocumentChunk, Lesson
from app.services.nevora_engine import enrich_with_llm


def tutor_reply(session: Session, profile_id: int, message: str, course_id: int | None, llm_provider: str):
    lessons = []
    if course_id:
        lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id).limit(3)).all()
    chunks = session.exec(select(DocumentChunk).where(DocumentChunk.profile_id == profile_id).limit(4)).all()
    cites = [{"type": "lesson", "id": l.id} for l in lessons] + [{"type": "chunk", "id": c.id} for c in chunks]

    if llm_provider == "ollama":
        context = "\n".join([l.title for l in lessons] + [c.text[:160] for c in chunks])
        prompt = f"Answer briefly. User: {message}\nContext:\n{context}"
        resp = enrich_with_llm(prompt)
        if resp:
            return {"response": resp[:1200], "citations": cites}

    tips = [
        "Review today's lesson objectives and complete one core task.",
        "Use 3 quick recall prompts from your notes before practice.",
        "End with a one-sentence reflection and one next step.",
    ]
    return {"response": f"Tutor (offline): {tips[0]} You asked: '{message[:120]}'.", "citations": cites}
