"""
Role API route integration tests.

Uses FastAPI's TestClient against a fresh in-memory SQLite registry —
no real Uvicorn server needed. The route handlers go through the same
ConnectionRegistry the production app uses.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import roles as roles_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base


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
    """Spin up an in-memory DB, register it, and return a TestClient."""
    factory = _shared_memory_factory()
    factory.create_tables(Base)

    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )

    app = FastAPI()
    app.include_router(roles_routes.router)

    return TestClient(app)


def test_post_role_creates_role(api_client):
    """POST /roles creates a role and returns it."""
    response = api_client.post("/roles", json={
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
    create_resp = api_client.post("/roles", json={
        "name": "editor",
        "description": "Editor"
    })
    assert create_resp.status_code == 200
    role_id = create_resp.json()["id"]

    get_resp = api_client.get(f"/roles/{role_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "editor"


def test_get_role_404_when_missing(api_client):
    """GET /roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.get(f"/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_roles_returns_all(api_client):
    """GET /roles returns all created roles."""
    api_client.post("/roles", json={"name": "admin", "description": "Admin"})
    api_client.post("/roles", json={"name": "editor", "description": "Editor"})

    response = api_client.get("/roles")
    assert response.status_code == 200
    assert len(response.json()["roles"]) == 2


def test_list_roles_returns_empty_when_none(api_client):
    """GET /roles on an empty database returns an empty roles list."""
    response = api_client.get("/roles")
    assert response.status_code == 200
    assert response.json()["roles"] == []


def test_delete_role_removes_it(api_client):
    """DELETE /roles/{id} removes the role; subsequent GET returns 404."""
    create_resp = api_client.post("/roles", json={
        "name": "viewer",
        "description": "Viewer"
    })
    role_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/roles/{role_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True

    get_resp = api_client.get(f"/roles/{role_id}")
    assert get_resp.status_code == 404


def test_delete_role_404_when_missing(api_client):
    """DELETE /roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.delete(f"/roles/{uuid.uuid4()}")
    assert response.status_code == 404
