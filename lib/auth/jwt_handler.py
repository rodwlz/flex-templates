import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from jose import JWTError  # noqa: F401 — re-exported so callers only import from here

_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60


def create_token(payload: dict, expire_minutes: int = _EXPIRE_MINUTES) -> str:
    """Return a signed JWT. payload must include 'sub' (user id string)."""
    data = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(data, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jose.JWTError if invalid or expired."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
