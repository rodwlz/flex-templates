"""
HTTP API integration tests.

Uses FastAPI's TestClient against a fresh in-memory SQLite registry — no
real Uvicorn server needed. The route handlers go through the same
ConnectionRegistry the production app uses.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import users as users_routes
from tests.conftest import _v1_app
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.repositories.user_repository import UserRepository


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
    """Spin up an in-memory DB, register it, and return a TestClient + repo."""
    factory = _shared_memory_factory()
    factory.create_tables(Base)

    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )

    app = _v1_app(users_routes.router)

    repo = UserRepository(factory)
    return TestClient(app), repo


def _make_user(repo, username="alice", email=None):
    return repo.create({
        "username": username,
        "email": email or f"{username}@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })


def test_get_user_returns_200_with_serialized_uuid(api_client):
    """GET /users/{uuid} returns the user with id stringified."""
    client, repo = api_client
    user = _make_user(repo)

    response = client.get(f"/v1/users/{user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    # New service-backed endpoint surfaces the user's roles too.
    assert body["roles"] == []


def test_get_user_404_when_missing(api_client):
    """A valid UUID that doesn't exist returns 404."""
    client, _ = api_client

    response = client.get(f"/v1/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_user_404_on_malformed_uuid(api_client):
    """A non-UUID id is parsed by the service layer; a parse failure surfaces as 404.

    The route param is now `str` (the service is the source of truth for id
    validity), so FastAPI no longer 422s before the handler runs. The service
    raises ValueError on uuid.UUID('not-a-uuid'), which becomes a 404.
    """
    client, _ = api_client

    response = client.get("/v1/users/not-a-uuid")

    assert response.status_code == 404


def test_list_users_returns_all(api_client):
    """GET /users returns every user in the database under the `users` key."""
    client, repo = api_client
    _make_user(repo, username="alice")
    _make_user(repo, username="bob")

    response = client.get("/v1/users")

    assert response.status_code == 200
    body = response.json()
    usernames = {u["username"] for u in body["users"]}
    assert usernames == {"alice", "bob"}


def test_list_users_returns_empty_list_when_no_users(api_client):
    """An empty database returns {'users': []}."""
    client, _ = api_client

    response = client.get("/v1/users")

    assert response.status_code == 200
    body = response.json()
    assert body["users"] == []
    assert body["total"] == 0
