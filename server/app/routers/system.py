from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health():
    return {"ok": True, "app": settings.app_name, "version": settings.app_version}
