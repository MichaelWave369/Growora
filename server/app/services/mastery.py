from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.models import EvidenceEvent, MasteryState


def bucket(theta: float) -> str:
    if theta < -0.5:
        return "New"
    if theta < 0.5:
        return "Learning"
    if theta < 1.5:
        return "Comfortable"
    return "Mastered"


def due_at(theta: float, last_seen_at: datetime | None) -> datetime:
    base = last_seen_at or datetime.utcnow()
    days = max(1, int(round(2 + theta * 2)))
    return base + timedelta(days=days)


def update_mastery(session: Session, profile_id: int, course_id: int, concept_id: int, kind: str, score: float, meta: dict | None = None):
    st = session.exec(select(MasteryState).where(MasteryState.profile_id == profile_id, MasteryState.course_id == course_id, MasteryState.concept_id == concept_id)).first()
    if not st:
        st = MasteryState(profile_id=profile_id, course_id=course_id, concept_id=concept_id, theta=0.0, sigma=1.0)
    delta = (score - 0.5) * 0.6
    st.theta = max(-3.0, min(3.0, st.theta + delta))
    st.sigma = max(0.2, st.sigma * 0.98)
    st.streak = st.streak + 1 if score >= 0.7 else 0
    st.last_seen_at = datetime.utcnow()
    st.updated_at = datetime.utcnow()
    session.add(st)
    session.add(EvidenceEvent(profile_id=profile_id, course_id=course_id, concept_id=concept_id, kind=kind, score=score, meta_json=str(meta or {})))
    session.commit(); session.refresh(st)
    return st
