import os
import sys
import warnings
from datetime import datetime, timedelta, timezone

from jose import jwt
from jose import JWTError  # noqa: F401 — re-exported so callers only import from here

_DEV_SECRET = "dev-secret-change-me"
_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEV_SECRET)
_ALGORITHM = "HS256"
_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", "60"))


def _check_jwt_secret(key: str, strict: bool) -> None:
    """Check if JWT secret is the insecure default and emit warning or exit.

    Args:
        key: The JWT secret key to check
        strict: If True, print error and exit(1); if False, emit warning
    """
    if key == _DEV_SECRET:
        _msg = (
            "JWT_SECRET_KEY is using the insecure default dev secret. "
            "Set JWT_SECRET_KEY in .secrets/.env before deploying."
        )
        if strict:
            print(f"ERROR: {_msg}", file=sys.stderr)
            sys.exit(1)
        else:
            warnings.warn(_msg, stacklevel=2)


# Check at module load — strict mode if jwt_strict or api_only
from lib.config.settings import AppConfig as _AppConfig
_config = _AppConfig()
_check_jwt_secret(_SECRET_KEY, strict=_config.jwt_strict or _config.api_only)


def create_token(payload: dict, expire_minutes: int = _EXPIRY_MINUTES) -> str:
    """Return a signed JWT. payload must include 'sub' (user id string)."""
    data = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(data, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jose.JWTError if invalid or expired."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
