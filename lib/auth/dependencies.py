import os

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette.websockets import WebSocketDisconnect

from lib.auth.jwt_handler import JWTError, decode_token

# AUTH_LOGIN_URL lets forked projects move the login endpoint without breaking Swagger UI.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl=os.getenv("AUTH_LOGIN_URL", "/v1/auth/login"))


def get_current_user(token: str = Depends(_oauth2_scheme)) -> dict:
    """FastAPI dependency: decode Bearer JWT, return {"id": ..., "roles": [...]}."""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"id": user_id, "roles": payload.get("roles", [])}
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_ws_user(token: str) -> dict:
    """Validate a JWT passed as ?token=<JWT> on WebSocket upgrade.

    Browsers cannot send Authorization headers during the WS handshake,
    so the token travels as a query parameter instead.

    Raises WebSocketDisconnect(code=4001) on missing subject or invalid token.
    """
    try:
        payload = decode_token(token)
        if not payload.get("sub"):
            raise WebSocketDisconnect(code=4001)
        return {"id": payload["sub"], "roles": payload.get("roles", [])}
    except JWTError:
        raise WebSocketDisconnect(code=4001)


def require_roles(*role_names: str):
    """Dependency factory: require the authenticated user to hold at least one role.

    Usage:
        @router.get("/admin")
        def admin_page(user=Depends(require_roles("admin", "superadmin"))):
            ...
    """
    if not role_names:
        raise ValueError("require_roles() requires at least one role name")

    def _check(user: dict = Depends(get_current_user)) -> dict:
        if not set(role_names).intersection(user.get("roles", [])):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of: {', '.join(role_names)}",
            )
        return user

    return _check
