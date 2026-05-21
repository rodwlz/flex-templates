"""
Authentication endpoints — OAuth2 password flow.

POST /auth/login accepts application/x-www-form-urlencoded with `username` and
`password` fields (OAuth2PasswordRequestForm). Returning a Bearer JWT keeps the
API compatible with any OAuth2-aware client and allows swapping in an external
provider later without changing callers.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService
from lib.auth.jwt_handler import create_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_service() -> UserService:
    return UserService(ConnectionRegistry.get())


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(_get_service),
):
    """Authenticate with username/email + password (OAuth2 password flow). Returns Bearer JWT."""
    result = service.execute(ActionRequest(
        action="authenticate",
        data={"username": form.username, "password": form.password},
    ))
    if not result.success:
        await asyncio.sleep(0.5)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_token({"sub": result.data["id"], "roles": result.data["roles"]})
    return {"access_token": token, "token_type": "bearer"}
