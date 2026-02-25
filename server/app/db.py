from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


engine = create_engine(settings.sqlite_url, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(text, document_id UNINDEXED, chunk_id UNINDEXED)"
        )
        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session
