from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.models import ClassroomEvent, EvidenceEvent, Profile, ReviewLog, SchemaVersion, SessionEvent


engine = create_engine(settings.sqlite_url, connect_args={"check_same_thread": False})
_db_ready = False


def _backfill_event_ids(session: Session) -> None:
    import uuid
    for model in (EvidenceEvent, SessionEvent, ClassroomEvent, ReviewLog):
        rows = session.exec(select(model)).all()
        changed = False
        for r in rows:
            if not getattr(r, 'global_event_id', None):
                setattr(r, 'global_event_id', str(uuid.uuid4()))
                changed = True
            if not getattr(r, 'device_id', None):
                setattr(r, 'device_id', 'host-local')
                changed = True
            if changed:
                session.add(r)
    session.commit()


def init_db() -> None:
    global _db_ready
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(text, document_id UNINDEXED, chunk_id UNINDEXED, profile_id UNINDEXED)"
        )
        conn.commit()

    with Session(engine) as session:
        if not session.exec(select(SchemaVersion)).first():
            session.add(SchemaVersion(version="0.3.0"))
        if not session.exec(select(Profile)).first():
            session.add(Profile(display_name="Default Learner", role="adult", timezone="UTC", day_start_time="06:00"))
        session.commit()
        _backfill_event_ids(session)
    _db_ready = True


def get_session():
    if not _db_ready:
        init_db()
    with Session(engine) as session:
        yield session
