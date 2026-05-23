"""
REST endpoints for the User resource — demonstrates all three operation styles.

The User resource is the canonical example of the framework's API architecture:

1. IMMEDIATE operations (POST/GET/DELETE on /users/{id})
   One-shot CRUD. The service commits straight away — no preview, no rollback.

2. STAGED operations (/users/with-roles/stage|confirm|cancel)
   For multi-step work that benefits from a preview. `stage` returns a diff and
   keeps the unit-of-work open; `confirm` commits it, `cancel` rolls back.

3. APPROVAL-REQUIRED operations (/users/bulk-delete/request|approve)
   The same staged flow, but flagged with `requires_approval=True` so callers
   (UI / clients) know an explicit second step is mandatory before commit.

All endpoints go through UserService.execute(ActionRequest(...)). Errors come
back as ActionResult(success=False, error=...) and are translated to 4xx HTTP.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


# UserService is a *StagingService* — it carries the in-flight unit-of-work in
# `self._pending` between stage() and confirm()/cancel(). The staged flow only
# works if the same instance handles the whole stage→confirm pair, so we cache
# one instance per registered factory rather than building a fresh service on
# every request the way a stateless service (e.g. RoleService) could.
_service_cache: dict[int, UserService] = {}


def get_service() -> UserService:
    factory = ConnectionRegistry.get()
    key = id(factory)
    service = _service_cache.get(key)
    if service is None:
        service = UserService(factory)
        _service_cache[key] = service
    return service


# ===== IMMEDIATE OPERATIONS =====

@router.post("", tags=["immediate"])
def create_user(data: dict, service: UserService = Depends(get_service)):
    """Create a user immediately (no roles attached)."""
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("", tags=["immediate"])
def list_users(
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(get_service),
):
    """List users with page/page_size pagination. Returns PaginatedResult shape."""
    result = service.execute(ActionRequest(
        action="list",
        data={"page": page, "page_size": page_size},
    ))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("/{user_id}", tags=["immediate"])
def get_user(user_id: str, service: UserService = Depends(get_service)):
    """Get a user (with roles) by id."""
    result = service.execute(ActionRequest(action="get", data={"id": user_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.delete("/{user_id}", tags=["immediate"])
def delete_user(user_id: str, service: UserService = Depends(get_service)):
    """Delete a user by id."""
    result = service.execute(ActionRequest(action="delete", data={"id": user_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


# ===== STAGED OPERATIONS (preview / confirm / cancel) =====

@router.post("/with-roles/stage", tags=["staged"])
def stage_user_with_roles(data: dict, service: UserService = Depends(get_service)):
    """Stage creation of a user with roles. Returns a preview diff."""
    result = service.execute(ActionRequest(action="stage", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/with-roles/confirm", tags=["staged"])
def confirm_user_with_roles(service: UserService = Depends(get_service)):
    """Commit the currently staged user-with-roles creation."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/with-roles/cancel", tags=["staged"])
def cancel_user_with_roles(service: UserService = Depends(get_service)):
    """Cancel the currently staged user-with-roles creation."""
    result = service.execute(ActionRequest(action="cancel", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


# ===== APPROVAL-REQUIRED OPERATIONS =====

@router.post("/bulk-delete/request", tags=["approval"])
def request_bulk_delete(data: dict, service: UserService = Depends(get_service)):
    """Stage a bulk delete with requires_approval=True — preview only, no commit."""
    request = ActionRequest(action="stage", data=data, requires_approval=True)
    result = service.execute(request)
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/bulk-delete/approve", tags=["approval"])
def approve_bulk_delete(data: dict, service: UserService = Depends(get_service)):
    """Approve and commit a previously staged bulk delete.

    In production the approval_key carried in `data` would be verified
    cryptographically before confirming. The route here demonstrates the shape
    of the flow — the safety check itself lives in the service / policy layer.
    """
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
