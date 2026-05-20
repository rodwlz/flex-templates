import os
import sys
import warnings
from datetime import datetime, timedelta, timezone

from jose import jwt
from jose import JWTError  # noqa: F401 — re-exported so callers only import from here

_DEV_SECRET = "dev-secret-change-in-production"
_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEV_SECRET)

if _SECRET_KEY == _DEV_SECRET:
    _msg = (
        "JWT_SECRET_KEY is using the insecure default dev secret. "
        "Set JWT_SECRET_KEY in your environment or .env before deploying."
    )
    if os.getenv("API_ONLY", "").lower() in ("1", "true", "yes"):
        # Hard fail in headless/production mode — forgeable tokens are critical
        print(f"ERROR: {_msg}", file=sys.stderr)
        sys.exit(1)
    else:
        warnings.warn(_msg, stacklevel=2)
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
