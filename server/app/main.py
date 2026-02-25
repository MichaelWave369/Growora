from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import init_db
from app.routers import backup, courses, drills, flashcards, forge, graph, library, profiles, progress, quizzes, sessions, studio, system, tutor

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(profiles.router)
app.include_router(courses.router)
app.include_router(progress.router)
app.include_router(quizzes.router)
app.include_router(flashcards.router)
app.include_router(library.router)
app.include_router(sessions.router)
app.include_router(forge.router)
app.include_router(tutor.router)
app.include_router(backup.router)
app.include_router(studio.router)
app.include_router(drills.router)
app.include_router(graph.router)


@app.on_event("startup")
def on_startup():
    init_db()
