import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.contracts.base import ActionRequest


def _shared_memory_factory() -> SessionFactory:
    """In-memory SQLite with StaticPool — keeps one connection alive so the
    schema created in setup is visible to route handlers in the test request."""
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
def auth_client(monkeypatch):
    """Auth-only TestClient backed by an in-memory DB with StaticPool."""
    import lib.models  # noqa: F401 — registers all ORM models in Base.metadata
    factory = _shared_memory_factory()
    factory.create_tables(Base)

    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})

    from lib.api.routes.auth import router as auth_router
    app = FastAPI()
    app.include_router(auth_router)
    return TestClient(app), factory


def _create_user(factory, username, email, password):
    from lib.services.user_service import UserService
    service = UserService(factory)
    service.execute(ActionRequest(action="create", data={
        "username": username, "email": email, "password": password,
    }))


def test_login_returns_bearer_token(auth_client):
    client, factory = auth_client
    _create_user(factory, "loginuser", "loginuser@test.com", "pass123")
    # OAuth2 form data — not JSON
    response = client.post("/auth/login", data={"username": "loginuser", "password": "pass123"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_token_is_decodable(auth_client):
    client, factory = auth_client
    _create_user(factory, "decodeuser", "decodeuser@test.com", "pass456")
    response = client.post("/auth/login", data={"username": "decodeuser", "password": "pass456"})
    token = response.json()["access_token"]
    from lib.auth.jwt_handler import decode_token
    payload = decode_token(token)
    assert "sub" in payload
    assert "roles" in payload


def test_login_wrong_password_returns_401(auth_client):
    client, factory = auth_client
    _create_user(factory, "wrongpwuser", "wrongpwuser@test.com", "correct")
    response = client.post("/auth/login", data={"username": "wrongpwuser", "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_user_returns_401(auth_client):
    client, factory = auth_client
    response = client.post("/auth/login", data={"username": "ghost", "password": "pw"})
    assert response.status_code == 401
