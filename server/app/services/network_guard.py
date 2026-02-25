from urllib.parse import urlparse

from app.core.config import settings


class NetworkGuardError(Exception):
    pass


def ensure_url_allowed(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if settings.growora_network_mode == "offline":
        if host not in {"localhost", "127.0.0.1"}:
            raise NetworkGuardError("Offline mode blocks non-localhost outbound network calls")
        return
    if host not in settings.allowed_hosts:
        raise NetworkGuardError(f"Host '{host}' not in GROWORA_ALLOWED_HOSTS")
