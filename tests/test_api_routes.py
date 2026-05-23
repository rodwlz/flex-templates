"""
Role and User API route integration tests.

Uses FastAPI's TestClient against a fresh in-memory SQLite registry —
no real Uvicorn server needed. The route handlers go through the same
ConnectionRegistry the production app uses.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import roles as roles_routes
from lib.api.routes import users as users_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from tests.conftest import _v1_app


def _shared_memory_factory() -> SessionFactory:
    """In-memory SQLite that keeps one connection alive — required when the
    schema creator and the route handler are different sessions."""
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
    """Spin up an in-memory DB, register it, and return a TestClient.

    Mounts both `roles` and `users` routers — the staged-user tests need to
    create a role first, and the role tests don't care whether the users
    router is also mounted.
    """
    factory = _shared_memory_factory()
    factory.create_tables(Base)

    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )

    app = _v1_app(roles_routes.router, users_routes.router)

    return TestClient(app)


def test_post_role_creates_role(api_client):
    """POST /roles creates a role and returns it."""
    response = api_client.post("/v1/roles", json={
        "name": "admin",
        "description": "Administrator"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert data["description"] == "Administrator"
    assert "id" in data


def test_get_role_retrieves_role(api_client):
    """GET /roles/{id} returns the role with that ID."""
    create_resp = api_client.post("/v1/roles", json={
        "name": "editor",
        "description": "Editor"
    })
    assert create_resp.status_code == 200
    role_id = create_resp.json()["id"]

    get_resp = api_client.get(f"/v1/roles/{role_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "editor"


def test_get_role_404_when_missing(api_client):
    """GET /roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.get(f"/v1/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_roles_returns_all(api_client):
    """GET /roles returns all created roles."""
    api_client.post("/v1/roles", json={"name": "admin", "description": "Admin"})
    api_client.post("/v1/roles", json={"name": "editor", "description": "Editor"})

    response = api_client.get("/v1/roles")
    assert response.status_code == 200
    assert len(response.json()["roles"]) == 2


def test_list_roles_returns_empty_when_none(api_client):
    """GET /roles on an empty database returns an empty roles list."""
    response = api_client.get("/v1/roles")
    assert response.status_code == 200
    assert response.json()["roles"] == []


def test_delete_role_removes_it(api_client):
    """DELETE /roles/{id} removes the role; subsequent GET returns 404."""
    create_resp = api_client.post("/v1/roles", json={
        "name": "viewer",
        "description": "Viewer"
    })
    role_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/v1/roles/{role_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True

    get_resp = api_client.get(f"/v1/roles/{role_id}")
    assert get_resp.status_code == 404


def test_delete_role_404_when_missing(api_client):
    """DELETE /roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.delete(f"/v1/roles/{uuid.uuid4()}")
    assert response.status_code == 404


# ===== USER ROUTES — IMMEDIATE OPERATIONS =====

def test_post_user_creates_user(api_client):
    """POST /users immediately creates and returns the user."""
    response = api_client.post("/v1/users", json={
        "username": "alice",
        "email": "alice@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_get_user_with_roles(api_client):
    """GET /users/{id} returns the user and a roles array (empty by default)."""
    create_resp = api_client.post("/v1/users", json={
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    user_id = create_resp.json()["id"]

    get_resp = api_client.get(f"/v1/users/{user_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["username"] == "bob"
    assert "roles" in body
    assert body["roles"] == []


def test_list_users(api_client):
    """GET /users returns every user under the 'users' key."""
    api_client.post("/v1/users", json={
        "username": "u1", "email": "u1@example.com",
        "password_hash": "h", "salt": "s",
    })
    api_client.post("/v1/users", json={
        "username": "u2", "email": "u2@example.com",
        "password_hash": "h", "salt": "s",
    })

    resp = api_client.get("/v1/users")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


def test_delete_user_removes_it(api_client):
    """DELETE /users/{id} removes the user; subsequent GET returns 404."""
    create_resp = api_client.post("/v1/users", json={
        "username": "eve", "email": "eve@example.com",
        "password_hash": "h", "salt": "s",
    })
    user_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/v1/users/{user_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True

    assert api_client.get(f"/v1/users/{user_id}").status_code == 404


# ===== USER ROUTES — STAGED OPERATIONS =====

def test_stage_user_with_roles(api_client):
    """POST /users/with-roles/stage returns a preview, then /confirm commits it."""
    role_resp = api_client.post("/v1/roles", json={"name": "admin", "description": "Admin"})
    role_id = role_resp.json()["id"]

    stage_resp = api_client.post("/v1/users/with-roles/stage", json={
        "username": "charlie",
        "email": "charlie@example.com",
        "password_hash": "hash",
        "salt": "salt",
        "role_ids": [role_id],
    })
    assert stage_resp.status_code == 200
    assert "preview" in stage_resp.json()

    confirm_resp = api_client.post("/v1/users/with-roles/confirm")
    assert confirm_resp.status_code == 200

    users = api_client.get("/v1/users").json()
    assert any(u["username"] == "charlie" for u in users["items"])


def test_cancel_staged_user(api_client):
    """POST /users/with-roles/cancel rolls back the staged creation."""
    api_client.post("/v1/users/with-roles/stage", json={
        "username": "dave",
        "email": "dave@example.com",
        "password_hash": "hash",
        "salt": "salt",
        "role_ids": [],
    })

    cancel_resp = api_client.post("/v1/users/with-roles/cancel")
    assert cancel_resp.status_code == 200

    users = api_client.get("/v1/users").json()
    assert not any(u["username"] == "dave" for u in users["items"])


# ===== USER ROUTES — APPROVAL-REQUIRED OPERATIONS =====

def test_bulk_delete_request_then_approve(api_client):
    """The approval-required flow: request stages, approve commits."""
    # Stage a user via the request endpoint (uses requires_approval=True).
    request_resp = api_client.post("/v1/users/bulk-delete/request", json={
        "username": "frank",
        "email": "frank@example.com",
        "password_hash": "hash",
        "salt": "salt",
        "role_ids": [],
    })
    assert request_resp.status_code == 200
    assert "preview" in request_resp.json()

    # Approve commits the staged operation.
    approve_resp = api_client.post("/v1/users/bulk-delete/approve", json={})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["confirmed"] is True
