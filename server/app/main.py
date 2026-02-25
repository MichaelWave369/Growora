from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import init_db
from app.routers import courses, flashcards, library, progress, quizzes, system

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(courses.router)
app.include_router(progress.router)
app.include_router(quizzes.router)
app.include_router(flashcards.router)
app.include_router(library.router)


@app.on_event("startup")
def on_startup():
    init_db()
