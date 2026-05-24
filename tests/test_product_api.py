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

from lib.database.session import ConnectionRegistry
from lib.database.base import Base
from lib.services.user_service import UserService
from tests.conftest import _v1_app, _http_mem_factory


@pytest.fixture
def api_client(monkeypatch):
    """In-memory DB registered as 'postgres', products routers mounted."""
    from lib.api.routes import products as products_routes

    factory = _http_mem_factory()
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


@pytest.fixture
def http_product_factory(monkeypatch):
    """In-memory DB registered as 'postgres'."""
    factory = _http_mem_factory()
    factory.create_tables(Base)

    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )

    return factory


@pytest.fixture
def product_client(http_product_factory):
    """In-memory DB registered as 'postgres', products routers mounted with auth."""
    from lib.api.routes import products as products_routes
    from lib.api.routes import auth as auth_routes

    # Mount products and auth routers for token generation
    app = _v1_app(
        auth_routes.router,
        products_routes.public_router,
        products_routes.router,
    )

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_token(http_product_factory, product_client):
    """Create a user and return a valid JWT token."""
    # Create test user using the same factory as product_client
    svc = UserService(http_product_factory)
    svc.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )

    # Login and get token
    login_resp = product_client.post(
        "/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


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


def test_patch_product_without_jwt_returns_401(api_client):
    """PATCH /v1/products/{id} with no Authorization header must return 401."""
    response = api_client.patch(f"/v1/products/{uuid.uuid4()}", json={"price": 5.00})
    assert response.status_code == 401


def test_delete_product_without_jwt_returns_401(api_client):
    """DELETE /v1/products/{id} with no Authorization header must return 401."""
    response = api_client.delete(f"/v1/products/{uuid.uuid4()}")
    assert response.status_code == 401


# ── Authenticated CRUD ────────────────────────────────────────────────────

def test_create_product_with_token(product_client, auth_token):
    """Create a product with a valid JWT token."""
    resp = product_client.post(
        "/v1/products",
        json={"name": "Widget", "price": 9.99},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Widget"
    assert body["price"] == 9.99
    assert "id" in body


def test_create_product_missing_name_returns_400(product_client, auth_token):
    """POST /v1/products without name field returns 400."""
    resp = product_client.post(
        "/v1/products",
        json={"price": 9.99},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 400


def test_get_product_returns_200(product_client, auth_token):
    """GET /v1/products/{id} returns the product."""
    create_resp = product_client.post(
        "/v1/products",
        json={"name": "Gadget", "price": 19.99},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    product_id = create_resp.json()["id"]
    resp = product_client.get(f"/v1/products/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Gadget"


def test_list_products_returns_paginated(product_client, auth_token):
    """GET /v1/products?page=1&page_size=2 returns paginated results."""
    for i in range(3):
        product_client.post(
            "/v1/products",
            json={"name": f"Item-{i}", "price": float(i + 1)},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    resp = product_client.get("/v1/products?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 3


def test_update_product_partial(product_client, auth_token):
    """PATCH /v1/products/{id} with partial data updates the product."""
    create_resp = product_client.post(
        "/v1/products",
        json={"name": "Original", "price": 5.00},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    product_id = create_resp.json()["id"]
    resp = product_client.patch(
        f"/v1/products/{product_id}",
        json={"price": 8.00},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["price"] == 8.0
    assert resp.json()["name"] == "Original"


def test_delete_product(product_client, auth_token):
    """DELETE /v1/products/{id} removes the product."""
    create_resp = product_client.post(
        "/v1/products",
        json={"name": "Disposable", "price": 1.00},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    product_id = create_resp.json()["id"]
    del_resp = product_client.delete(
        f"/v1/products/{product_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert del_resp.status_code == 204

    get_resp = product_client.get(f"/v1/products/{product_id}")
    assert get_resp.status_code == 404


def test_update_nonexistent_product_returns_404(product_client, auth_token):
    """PATCH /v1/products/{nonexistent-id} returns 404."""
    resp = product_client.patch(
        f"/v1/products/{uuid.uuid4()}",
        json={"price": 99.99},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 404
