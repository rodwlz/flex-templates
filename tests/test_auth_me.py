"""Integration test for GET /v1/auth/me."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import auth as auth_routes
from lib.api.routes import users as users_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.services.user_service import UserService


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
def auth_client(monkeypatch):
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    svc = UserService(factory)
    svc.create_user(username="alice", email="alice@example.com", password="pass123")
    app = FastAPI()
    app.include_router(auth_routes.router)
    app.include_router(users_routes.router)
    return TestClient(app)


def test_me_returns_user_profile(auth_client):
    login = auth_client.post(
        "/v1/auth/login",
        data={"username": "alice", "password": "pass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = auth_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password_hash" not in body


def test_me_returns_401_without_token(auth_client):
    response = auth_client.get("/v1/auth/me")
    assert response.status_code == 401
