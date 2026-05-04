"""
HTTP API integration tests.

Uses FastAPI's TestClient against a fresh in-memory SQLite registry — no
real Uvicorn server needed. The route handlers go through the same
ConnectionRegistry the production app uses.
"""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import users as users_routes
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

    app = FastAPI()
    app.include_router(users_routes.router)

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

    response = client.get(f"/users/{user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"


def test_get_user_404_when_missing(api_client):
    """A valid UUID that doesn't exist returns 404."""
    client, _ = api_client

    response = client.get(f"/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_user_422_on_malformed_uuid(api_client):
    """A non-UUID id is rejected by FastAPI's path validation, not by the handler."""
    client, _ = api_client

    response = client.get("/users/not-a-uuid")

    assert response.status_code == 422


def test_list_users_returns_all(api_client):
    """GET /users/ returns every user in the database."""
    client, repo = api_client
    _make_user(repo, username="alice")
    _make_user(repo, username="bob")

    response = client.get("/users/")

    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert usernames == {"alice", "bob"}


def test_list_users_returns_empty_list_when_no_users(api_client):
    """An empty database returns []."""
    client, _ = api_client

    response = client.get("/users/")

    assert response.status_code == 200
    assert response.json() == []
