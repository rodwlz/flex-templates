"""
Authentication endpoints — OAuth2 password flow.

POST /v1/auth/login  accepts application/x-www-form-urlencoded (OAuth2PasswordRequestForm).
GET  /v1/auth/me     returns the authenticated user's profile (requires Bearer JWT).
"""
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from lib.auth.dependencies import get_current_user
from lib.auth.jwt_handler import create_token
from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _get_service() -> UserService:
    return UserService(ConnectionRegistry.get())


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(_get_service),
):
    """Authenticate with username/email + password (OAuth2 password flow). Returns Bearer JWT."""
    result = service.execute(ActionRequest(
        action="authenticate",
        data={"username": form.username, "password": form.password},
    ))
    if not result.success:
        time.sleep(0.5)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_token({"sub": result.data["id"], "roles": result.data["roles"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(
    current: dict = Depends(get_current_user),
    service: UserService = Depends(_get_service),
):
    """Return the authenticated user's full profile (id, username, email, roles)."""
    result = service.execute(ActionRequest(action="get", data={"id": current["id"]}))
    if not result.success:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data
