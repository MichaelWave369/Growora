import json
from pathlib import Path
from pypdf import PdfReader
from sqlmodel import Session

from app.models import Course, Lesson, Week

TEMPLATES = {
    "Kids Math": "numbers addition subtraction",
    "Coding Basics": "variables loops functions",
    "Guitar Beginner": "chords rhythm strumming",
    "Tech for Seniors": "phone email browser safety",
}


def create_draft_course(session: Session, profile_id: int, title: str, topic: str, template: str | None = None):
    c = Course(profile_id=profile_id, title=title, topic=topic, learner_profile_json=json.dumps({"template": template or "custom"}))
    session.add(c); session.commit(); session.refresh(c)
    w = Week(course_id=c.id, index=1, objectives_json=json.dumps(["Draft objective"]))
    session.add(w); session.commit(); session.refresh(w)
    seed = TEMPLATES.get(template or "", topic)
    for i, part in enumerate(seed.split()[:6], start=1):
        session.add(Lesson(course_id=c.id, week_id=w.id, day_index=i, order_index=i, title=f"{part.title()} basics", content_md=f"# {part}\n\nDraft lesson", exercises_json=json.dumps([f"Practice {part}"]), quiz_json=json.dumps({"questions": []})))
    session.commit()
    return c


def generate_lessons(session: Session, lesson_ids: list[int]):
    for lid in lesson_ids:
        l = session.get(Lesson, lid)
        if l:
            l.content_md += "\n\n## Generated practice\n- Do a 5-minute recap\n- Complete one microdrill"
            session.add(l)
    session.commit()


def import_markdown(session: Session, profile_id: int, title: str, markdown_text: str):
    c = Course(profile_id=profile_id, title=title, topic=title, learner_profile_json='{}')
    session.add(c); session.commit(); session.refresh(c)
    w = Week(course_id=c.id, index=1, objectives_json=json.dumps(["Imported from markdown"]))
    session.add(w); session.commit(); session.refresh(w)
    chunks = [x.strip() for x in markdown_text.split('\n# ') if x.strip()]
    for i, ch in enumerate(chunks[:20], start=1):
        title_line = ch.splitlines()[0][:80]
        session.add(Lesson(course_id=c.id, week_id=w.id, day_index=i, order_index=i, title=title_line, content_md="# "+ch if not ch.startswith('#') else ch, exercises_json='["Read and summarize"]', quiz_json='{"questions":[]}'))
    session.commit(); return c


def import_pdf_outline(session: Session, profile_id: int, title: str, path: Path):
    text = ''
    try:
        reader = PdfReader(str(path))
        text = '\n'.join((p.extract_text() or '') for p in reader.pages[:10])
    except Exception:
        text = 'PDF outline extraction partial. Continue editing in Studio.'
    return import_markdown(session, profile_id, title, f"# Outline\n{text[:4000]}")
