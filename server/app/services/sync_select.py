import json
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.models import Certificate, ClassroomEvent, ConceptEdge, EvidenceEvent, MasteryState, ReviewLog, SessionEvent


DEFAULT_TYPES = ["evidence", "mastery", "flashcards", "sessions", "certificates", "classroom"]


def _as_dt(v: str | None):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return None


def expand_concept_selection(
    session: Session,
    concept_ids: list[int],
    include_prereqs: bool = False,
    include_dependents: bool = False,
) -> list[int]:
    expanded = set(concept_ids or [])
    if not expanded:
        return []
    if include_prereqs or include_dependents:
        edges = session.exec(select(ConceptEdge)).all()
        changed = True
        while changed:
            changed = False
            for e in edges:
                if include_prereqs and e.dst_concept_id in expanded and e.src_concept_id not in expanded:
                    expanded.add(e.src_concept_id); changed = True
                if include_dependents and e.src_concept_id in expanded and e.dst_concept_id not in expanded:
                    expanded.add(e.dst_concept_id); changed = True
    return sorted(expanded)


def _select_events(rows: list[Any], course_ids: set[int], concept_ids: set[int], date_from, date_to, max_events: int, course_attr: str = 'course_id', concept_attr: str = 'concept_id', ts_attr: str = 'ts'):
    out = []
    for r in rows:
        c = getattr(r, course_attr, None)
        k = getattr(r, concept_attr, None)
        t = getattr(r, ts_attr, None)
        if course_ids and c not in course_ids:
            continue
        if concept_ids and k is not None and k not in concept_ids:
            continue
        if date_from and t and t < date_from:
            continue
        if date_to and t and t > date_to:
            continue
        out.append(r)
        if len(out) >= max_events:
            break
    return out


def build_selection_data(session: Session, profile_id: int, selection: dict[str, Any]) -> dict[str, Any]:
    types = selection.get('types') or DEFAULT_TYPES
    course_ids = set(selection.get('courses') or [])
    concepts = selection.get('concepts') or []
    expanded_concepts = expand_concept_selection(
        session,
        concepts,
        bool(selection.get('include_prereqs')),
        bool(selection.get('include_dependents')),
    )
    concept_ids = set(expanded_concepts)

    max_events = int(selection.get('max_events') or 1000)
    if max_events <= 0:
        max_events = 1000
    max_events = min(max_events, 10000)

    date_from = _as_dt((selection.get('date_range') or {}).get('from'))
    date_to = _as_dt((selection.get('date_range') or {}).get('to'))
    last_days = selection.get('last_days')
    if last_days and not date_from:
        date_from = datetime.utcnow() - timedelta(days=int(last_days))

    payload: dict[str, Any] = {
        'selection': {
            'profiles': [profile_id],
            'courses': sorted(course_ids),
            'concepts': expanded_concepts,
            'types': types,
            'date_range': {'from': date_from.isoformat() if date_from else None, 'to': date_to.isoformat() if date_to else None},
            'last_days': last_days,
            'max_events': max_events,
        },
        'counts_by_type': {},
    }

    if 'evidence' in types:
        rows = session.exec(select(EvidenceEvent).where(EvidenceEvent.profile_id == profile_id).order_by(EvidenceEvent.ts.desc())).all()
        picked = _select_events(rows, course_ids, concept_ids, date_from, date_to, max_events)
        payload['learning_events'] = [r.model_dump(mode='json') for r in picked]
        payload['counts_by_type']['evidence'] = len(picked)

    if 'mastery' in types:
        rows = session.exec(select(MasteryState).where(MasteryState.profile_id == profile_id)).all()
        picked = _select_events(rows, course_ids, concept_ids, date_from, date_to, max_events, ts_attr='updated_at')
        payload['mastery_snapshots'] = [r.model_dump(mode='json') for r in picked]
        payload['counts_by_type']['mastery'] = len(picked)

    if 'flashcards' in types:
        rows = session.exec(select(ReviewLog).where(ReviewLog.profile_id == profile_id).order_by(ReviewLog.reviewed_at.desc())).all()
        # review logs don't include course/concept directly in current schema
        picked = _select_events(rows, set(), set(), date_from, date_to, max_events, concept_attr='flashcard_id', ts_attr='reviewed_at')
        payload['review_logs'] = [r.model_dump(mode='json') for r in picked]
        payload['counts_by_type']['flashcards'] = len(picked)

    if 'sessions' in types:
        rows = session.exec(select(SessionEvent).order_by(SessionEvent.ts.desc())).all()
        picked = _select_events(rows, set(), set(), date_from, date_to, max_events)
        payload['session_events'] = [r.model_dump(mode='json') for r in picked]
        payload['counts_by_type']['sessions'] = len(picked)

    if 'classroom' in types:
        rows = session.exec(select(ClassroomEvent).order_by(ClassroomEvent.ts.desc())).all()
        picked = _select_events(rows, set(), set(), date_from, date_to, max_events)
        payload['classroom_events'] = [r.model_dump(mode='json') for r in picked]
        payload['counts_by_type']['classroom'] = len(picked)

    if 'certificates' in types:
        rows = session.exec(select(Certificate).where(Certificate.profile_id == profile_id)).all()
        picked = _select_events(rows, course_ids, set(), date_from, date_to, max_events, concept_attr='id', ts_attr='issued_at')
        payload['certificates'] = [r.model_dump(mode='json') for r in picked]
        payload['counts_by_type']['certificates'] = len(picked)

    payload['courses_included'] = sorted({e.get('course_id') for e in payload.get('learning_events', []) if e.get('course_id') is not None} | course_ids)
    payload['concepts_included'] = sorted({e.get('concept_id') for e in payload.get('learning_events', []) if e.get('concept_id') is not None} | concept_ids)
    payload['estimated_size'] = len(json.dumps(payload).encode('utf-8'))
    return payload
