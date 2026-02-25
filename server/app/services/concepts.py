import re
from collections import Counter
from sqlmodel import Session, select

from app.models import Concept, ConceptEdge, ConceptLessonLink, DocumentChunk, Lesson, StudySession

STOP = set('the and of to a for in on is are as with by from your you this that'.split())


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]


def _extract_terms(text: str):
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9\-']+", text)]
    words = [w for w in words if w not in STOP and len(w) > 2]
    return words


def rebuild_graph(session: Session, profile_id: int, course_id: int, max_concepts: int = 80):
    lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
    chunks = session.exec(select(DocumentChunk).where(DocumentChunk.profile_id == profile_id).limit(200)).all()
    notes = session.exec(select(StudySession).where(StudySession.profile_id == profile_id, StudySession.course_id == course_id)).all()

    corpus = []
    for l in lessons: corpus.append((f"lesson:{l.id}", l.content_md))
    for c in chunks: corpus.append((f"chunk:{c.id}", c.text))
    for n in notes: corpus.append((f"note:{n.id}", n.notes_md or ''))

    cnt = Counter()
    for _, t in corpus: cnt.update(_extract_terms(t))
    terms = [t for t, _ in cnt.most_common(max_concepts)]

    existing = session.exec(select(Concept).where(Concept.profile_id == profile_id, Concept.course_id == course_id)).all()
    for e in existing: session.delete(e)
    for e in session.exec(select(ConceptEdge).where(ConceptEdge.profile_id == profile_id, ConceptEdge.course_id == course_id)).all(): session.delete(e)
    for e in session.exec(select(ConceptLessonLink).where(ConceptLessonLink.profile_id == profile_id, ConceptLessonLink.course_id == course_id)).all(): session.delete(e)
    session.commit()

    concepts = []
    for t in terms:
        c = Concept(profile_id=profile_id, course_id=course_id, slug=_slug(t), title=t.title(), description=f"Concept about {t}")
        session.add(c); session.commit(); session.refresh(c)
        concepts.append(c)

    # link concepts to lessons and heuristic edges
    for l in lessons:
        low = l.content_md.lower()
        linked = [c for c in concepts if c.slug.replace('-', ' ')[:20].split(' ')[0] in low]
        for c in linked[:8]:
            session.add(ConceptLessonLink(profile_id=profile_id, course_id=course_id, concept_id=c.id, lesson_id=l.id, strength=0.6))
    for i in range(len(concepts)-1):
        session.add(ConceptEdge(profile_id=profile_id, course_id=course_id, src_concept_id=concepts[i].id, dst_concept_id=concepts[i+1].id, kind='prereq', weight=0.4))
    session.commit()
    return {"concept_count": len(concepts), "edge_count": max(0, len(concepts)-1)}
