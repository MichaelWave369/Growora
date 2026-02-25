import json
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.models import (
    Assignment,
    Classroom,
    ClassroomEvent,
    ClassroomMember,
    ClassroomSession,
    ClassroomSessionMember,
    Concept,
    LiveQuiz,
    LiveQuizResponse,
    MasteryState,
    SlideDeck,
    TeachbackPrompt,
    TeachbackSubmission,
)
from app.services.mastery import update_mastery


def create_deck_from_text(session_id: int, title: str, text: str):
    bullets = [x.strip() for x in text.splitlines() if x.strip()][:16]
    slides = [
        {"title": title, "notes": "overview"},
        {"title": "Key points", "bullets": bullets[:5]},
        {"title": "Worked example", "content": bullets[5:10]},
        {"title": "Practice prompt", "prompt": "Try explaining this concept to a peer."},
    ]
    return slides[:8]


def teachback_score(response_text: str, concept_desc: str):
    text = response_text.lower()
    keys = [w for w in concept_desc.lower().split() if len(w) > 3][:12]
    hit = sum(1 for k in keys if k in text)
    base = min(4, int(round((hit / max(1, len(keys))) * 4)))
    out = {
        "correctness": base,
        "completeness": min(4, base + (1 if len(text) > 80 else 0)),
        "clarity": min(4, 2 if len(text) > 30 else 1),
        "example_usage": 1 if "example" in text else 0,
    }
    return out


def whiteboard_path(session_id: int) -> Path:
    p = Path(f"server/data/whiteboards/{session_id}")
    p.mkdir(parents=True, exist_ok=True)
    return p


def classroom_summary(session: Session, session_id: int):
    s = session.get(ClassroomSession, session_id)
    members = session.exec(select(ClassroomSessionMember).where(ClassroomSessionMember.session_id == session_id)).all()
    quizzes = session.exec(select(LiveQuiz).where(LiveQuiz.session_id == session_id)).all()
    qids = [q.id for q in quizzes]
    qres = [r for r in session.exec(select(LiveQuizResponse)).all() if r.live_quiz_id in qids]
    prompts = session.exec(select(TeachbackPrompt).where(TeachbackPrompt.session_id == session_id)).all()
    pids = [p.id for p in prompts]
    tsubs = [t for t in session.exec(select(TeachbackSubmission)).all() if t.prompt_id in pids]
    mastery = session.exec(select(MasteryState)).all()

    attend = [{"profile_id": m.profile_id, "joined_at": str(m.joined_at), "left_at": str(m.left_at) if m.left_at else None} for m in members]
    quiz_scores = [{"profile_id": r.profile_id, "score": r.score} for r in qres]
    teach_scores = []
    for t in tsubs:
        sj = json.loads(t.score_json)
        teach_scores.append({"profile_id": t.profile_id, "total": sum(sj.values())})
    weak = sorted([m for m in mastery if m.course_id == s.course_id], key=lambda x: x.theta)[:5]

    return {
        "attendance": attend,
        "minutes_engaged": [{"profile_id": m.profile_id, "minutes": 15} for m in members],
        "quiz_scores": quiz_scores,
        "teachback_scores": teach_scores,
        "top_weak_concepts": [{"concept_id": w.concept_id, "theta": w.theta} for w in weak],
        "recommended_next_steps": ["Open /today for each learner", "Assign 1-2 microdrills", "Run short review session"],
    }
