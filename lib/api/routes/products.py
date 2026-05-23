"""
REST endpoints for the Product resource — demonstrates the mixed-auth pattern.

GETs (list + detail) are mounted on `public_router` and require no Bearer token.
Writes (create, update, delete) are mounted on `router` and require a valid JWT.

The router_registry picks up both:
  - `public_router`  → mounted into the public sub-router (no auth)
  - `router`         → mounted into the protected sub-router (JWT required)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from lib.auth.dependencies import get_current_user
from lib.contracts.base import ActionRequest, PaginatedResult
from lib.database.session import ConnectionRegistry
from lib.services.product_service import ProductService


public_router = APIRouter(prefix="/products", tags=["products"])
router = APIRouter(prefix="/products", tags=["products"])


def _get_service() -> ProductService:
    return ProductService(ConnectionRegistry.get())


# ── public read endpoints ─────────────────────────────────────────────────────

@public_router.get("", response_model=PaginatedResult)
def list_products(page: int = 1, page_size: int = 20):
    """List products with pagination. No authentication required."""
    svc = _get_service()
    result = svc.execute(ActionRequest(
        action="list",
        data={"page": page, "page_size": page_size},
    ))
    if not result.success:
        # 400: list failures are bad-input errors, not resource-not-found
        raise HTTPException(400, detail=result.error)
    return result.data


@public_router.get("/{product_id}")
def get_product(product_id: uuid.UUID):
    """Get a product by id. No authentication required."""
    svc = _get_service()
    result = svc.execute(ActionRequest(action="get", data={"id": str(product_id)}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


# ── protected write endpoints (JWT required) ──────────────────────────────────

@router.post("", status_code=201)
def create_product(data: dict, _user=Depends(get_current_user)):
    """Create a product. Requires a valid Bearer JWT."""
    svc = _get_service()
    result = svc.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.patch("/{product_id}")
def update_product(product_id: uuid.UUID, data: dict, _user=Depends(get_current_user)):
    """Update a product by id. Requires a valid Bearer JWT."""
    svc = _get_service()
    result = svc.execute(ActionRequest(
        action="update",
        data={"id": str(product_id), **data},
    ))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: uuid.UUID, _user=Depends(get_current_user)):
    """Delete a product by id. Requires a valid Bearer JWT."""
    svc = _get_service()
    result = svc.execute(ActionRequest(action="delete", data={"id": str(product_id)}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
