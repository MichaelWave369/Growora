import base64
import hashlib
import os
import socket
from datetime import datetime, timedelta


def random_code(n: int = 8) -> str:
    raw = base64.b32encode(os.urandom(5)).decode().strip("=")
    return raw[:n]


def random_token() -> str:
    return base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip('=')


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def local_ips() -> list[str]:
    ips = set(["127.0.0.1"])
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    return sorted(ips)


def expires_in(minutes: int):
    return datetime.utcnow() + timedelta(minutes=minutes)
