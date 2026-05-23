"""
REST endpoints for the Role resource.

Uses RoleService (SimpleService) for CRUD. assign/remove go through
UserRepository directly because they are user↔role relationship ops.
Role.id is uuid.UUID — FastAPI parses it from the URL automatically.

IMPORTANT: /assign and /remove are declared BEFORE /{role_id} to prevent
FastAPI from treating "assign"/"remove" as role ID path parameters.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.repositories.user_repository import UserRepository
from lib.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -> RoleService:
    return RoleService(ConnectionRegistry.get())


class _RoleAssignment(BaseModel):
    user_id: str
    role_id: str


@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
    """Create a new role."""
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("")
def list_roles(service: RoleService = Depends(get_service)):
    """List all roles."""
    result = service.execute(ActionRequest(action="list", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/assign")
def assign_role(body: _RoleAssignment):
    """Assign a role to a user."""
    repo = UserRepository(ConnectionRegistry.get())
    result = repo.add_role(uuid.UUID(body.user_id), uuid.UUID(body.role_id))
    if not result:
        raise HTTPException(404, detail="User or role not found")
    return {"assigned": True}


@router.delete("/remove")
def remove_role(body: _RoleAssignment):
    """Remove a role from a user."""
    repo = UserRepository(ConnectionRegistry.get())
    result = repo.remove_role(uuid.UUID(body.user_id), uuid.UUID(body.role_id))
    if not result:
        raise HTTPException(404, detail="Assignment not found")
    return {"removed": True}


@router.get("/{role_id}")
def get_role(role_id: str, service: RoleService = Depends(get_service)):
    """Get a role by ID."""
    result = service.execute(ActionRequest(action="get", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.delete("/{role_id}")
def delete_role(role_id: str, service: RoleService = Depends(get_service)):
    """Delete a role."""
    result = service.execute(ActionRequest(action="delete", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data
