from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import init_db
from app.routers import (
    backup,
    classrooms,
    courses,
    drills,
    flashcards,
    forge,
    graph,
    lan,
    library,
    network,
    profiles,
    progress,
    quizzes,
    sessions,
    settings_network,
    studio,
    system,
    tutor,
)

app = FastAPI(title=settings.app_name, version=settings.app_version)
origins = [o.strip() for o in settings.cors_origins.split(',') if o.strip()] + [o.strip() for o in settings.growora_allowed_origins.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(network.router)
app.include_router(settings_network.router)
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
app.include_router(classrooms.router)
app.include_router(lan.router)


@app.on_event("startup")
def on_startup():
    init_db()
