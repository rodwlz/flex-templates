"""
Authentication endpoints — OAuth2 password flow.

POST /v1/auth/login  accepts application/x-www-form-urlencoded (OAuth2PasswordRequestForm).
GET  /v1/auth/me     returns the authenticated user's profile (requires Bearer JWT).
"""
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from lib.auth.dependencies import get_current_user
from lib.auth.jwt_handler import create_token
from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService

_PUBLIC_ROUTER = True  # mount into public sub-router — login needs no Bearer
router = APIRouter(prefix="/auth", tags=["auth"])


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


# ── Registration ──────────────────────────────────────────────────────────────

class _RegisterBody(BaseModel):
    username: str
    email: str
    password: str


@router.post("/register", status_code=201)
def register(body: _RegisterBody, service: UserService = Depends(_get_service)):
    """Create a new user account. Returns user_id, username, is_active."""
    result = service.execute(ActionRequest(action="register", data={
        "username": body.username,
        "email": body.email,
        "password": body.password,
    }))
    if not result.success:
        if result.error and "already registered" in result.error:
            raise HTTPException(status_code=409, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "user_id": result.data["id"],
        "username": result.data["username"],
        "is_active": result.data["is_active"],
    }


# ── Password reset ────────────────────────────────────────────────────────────

class _ForgotPasswordBody(BaseModel):
    email: str


class _ResetPasswordBody(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(body: _ForgotPasswordBody, service: UserService = Depends(_get_service)):
    """Request a password reset token. Always 200 — token in body (no email service in dev)."""
    result = service.execute(ActionRequest(
        action="request_reset",
        data={"email": body.email},
    ))
    return result.data


@router.post("/reset-password")
def reset_password(body: _ResetPasswordBody, service: UserService = Depends(_get_service)):
    """Reset password using a valid token. Returns 400 for invalid/expired tokens."""
    result = service.execute(ActionRequest(
        action="reset_password",
        data={"token": body.token, "new_password": body.new_password},
    ))
    if not result.success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return result.data
