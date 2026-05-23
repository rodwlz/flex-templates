"""
Basic wiring tests for the products API routes.

Verifies that:
- GET /v1/products is publicly accessible (no auth required)
- GET /v1/products/<nonexistent-uuid> returns 404 (no auth required)
- POST /v1/products without a JWT returns 401

Full CRUD tests come in Task 5.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from tests.conftest import _v1_app


def _shared_memory_factory() -> SessionFactory:
    """In-memory SQLite with a single persistent connection."""
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def api_client(monkeypatch):
    """In-memory DB registered as 'postgres', products routers mounted."""
    from lib.api.routes import products as products_routes

    factory = _shared_memory_factory()
    factory.create_tables(Base)

    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )

    # Mount both routers — public_router (unauthenticated GETs) and
    # router (JWT-protected writes).  _v1_app wraps them under /v1 with no
    # auth enforcement of its own, so the 401 must come from the Depends on
    # the write router itself.
    app = _v1_app(products_routes.public_router, products_routes.router)

    return TestClient(app, raise_server_exceptions=False)


# ── public read endpoints ─────────────────────────────────────────────────────

def test_list_products_returns_200_no_auth(api_client):
    """GET /v1/products is publicly accessible and returns an empty list."""
    response = api_client.get("/v1/products")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_get_product_404_when_missing(api_client):
    """GET /v1/products/<nonexistent-uuid> returns 404 without auth."""
    missing_id = uuid.uuid4()
    response = api_client.get(f"/v1/products/{missing_id}")
    assert response.status_code == 404


# ── protected write endpoints ─────────────────────────────────────────────────

def test_post_product_without_jwt_returns_401(api_client):
    """POST /v1/products with no Authorization header must return 401."""
    response = api_client.post("/v1/products", json={
        "name": "Widget",
        "price": 9.99,
    })
    assert response.status_code == 401
