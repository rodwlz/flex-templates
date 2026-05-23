"""Integration tests for POST /v1/roles/assign and DELETE /v1/roles/remove."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import roles as roles_routes
from lib.api.routes import users as users_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.services.user_service import UserService
from lib.services.role_service import RoleService
from tests.conftest import _v1_app


def _mem_factory():
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
def assign_client(monkeypatch):
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    app = _v1_app(roles_routes.router, users_routes.router)
    return TestClient(app), factory


def test_assign_role_returns_200(assign_client):
    client, factory = assign_client
    user = UserService(factory).create_user("bob", "bob@x.com", "pass")
    role = RoleService(factory).create_role("admin")

    resp = client.post("/v1/roles/assign", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    assert resp.status_code == 200
    assert resp.json()["assigned"] is True


def test_assign_role_404_on_bad_ids(assign_client):
    client, _ = assign_client
    import uuid
    resp = client.post("/v1/roles/assign", json={
        "user_id": str(uuid.uuid4()), "role_id": str(uuid.uuid4())
    })
    assert resp.status_code == 404


def test_remove_role_returns_200(assign_client):
    client, factory = assign_client
    user = UserService(factory).create_user("carol", "carol@x.com", "pass")
    role = RoleService(factory).create_role("editor")

    client.post("/v1/roles/assign", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    resp = client.request("DELETE", "/v1/roles/remove", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    assert resp.status_code == 200
    assert resp.json()["removed"] is True


def test_remove_role_404_when_not_assigned(assign_client):
    client, factory = assign_client
    user = UserService(factory).create_user("dave", "dave@x.com", "pass")
    role = RoleService(factory).create_role("viewer")

    resp = client.request("DELETE", "/v1/roles/remove", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    assert resp.status_code == 404
