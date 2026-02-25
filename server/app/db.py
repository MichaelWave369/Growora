from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.models import Profile, SchemaVersion


engine = create_engine(settings.sqlite_url, connect_args={"check_same_thread": False})


def init_db() -> None:
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


def get_session():
    with Session(engine) as session:
        yield session
