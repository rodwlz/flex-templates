"""
Manual REST endpoints for the User resource.

Path-param REST style (GET /users/{id}) needs FastAPI's path parsing, so
this is a manual APIRouter rather than mount_service. User.id is uuid.UUID
— FastAPI parses and validates it from the URL automatically.
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException

from lib.database.session import ConnectionRegistry
from lib.repositories.user_repository import UserRepository


router = APIRouter(prefix="/users", tags=["users"])


def get_repo() -> UserRepository:
    return UserRepository(ConnectionRegistry.get())


def _serialize(user) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
    }


@router.get("/")
def list_users(repo: UserRepository = Depends(get_repo)):
    return [_serialize(u) for u in repo.list()]


@router.get("/{id}")
def get_user(id: uuid.UUID, repo: UserRepository = Depends(get_repo)):
    user = repo.get(id)
    if user is None:
        raise HTTPException(404, "User not found")
    return _serialize(user)
