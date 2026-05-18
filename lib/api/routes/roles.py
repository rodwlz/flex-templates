"""
REST endpoints for the Role resource.

Uses RoleService (SimpleService) for immediate CRUD — no staging required.
Role.id is uuid.UUID — FastAPI parses and validates it from the URL automatically.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.database.session import ConnectionRegistry
from lib.services.role_service import RoleService
from lib.contracts.base import ActionRequest

router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -> RoleService:
    return RoleService(ConnectionRegistry.get())


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
