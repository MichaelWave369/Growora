import httpx

from app.core.config import settings
from app.services.network_guard import NetworkGuardError, ensure_url_allowed


def publish_coevo(course_zip_bytes: bytes, metadata: dict, dry_run: bool):
    if not settings.coevo_url or not settings.coevo_api_key:
        return {"ok": False, "status": "disabled", "detail": "Set COEVO_URL and COEVO_API_KEY first"}
    try:
        ensure_url_allowed(settings.coevo_url)
    except NetworkGuardError as exc:
        return {"ok": False, "status": "blocked", "detail": str(exc)}
    if dry_run:
        return {"ok": True, "status": "dry_run", "detail": "Dry run success. No data sent."}

    headers = {"Authorization": f"Bearer {settings.coevo_api_key}"}
    files = {"file": ("course.zip", course_zip_bytes, "application/zip")}
    data = {"metadata": str(metadata)}
    r = httpx.post(settings.coevo_url, headers=headers, files=files, data=data, timeout=30)
    if r.status_code >= 400:
        return {"ok": False, "status": "error", "detail": r.text}
    return {"ok": True, "status": "published", "detail": r.text[:500]}
