"""
Runtime security behaviour — auth flow, 401 rejection, and 429 rate limiting.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.config.settings import AppConfig
from lib.api.router_registry import mount_routes
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
def secured_client(monkeypatch):
    """Full v1 stack with a test user. Low rate limits so 429 tests trigger fast."""
    import lib.models  # noqa: F401
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    config = AppConfig(rate_limit_per_minute=5, rate_limit_login_per_minute=3)
    app = FastAPI()
    mount_routes(app, config)
    UserService(factory).create_user(
        username="sectest", email="sec@test.com", password="pass123"
    )
    return TestClient(app)


def _login(client) -> str:
    """Log in as sectest; return the Bearer token string."""
    resp = client.post(
        "/v1/auth/login", data={"username": "sectest", "password": "pass123"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth flow ──────────────────────────────────────────────────────────────

def test_login_returns_bearer_token(secured_client):
    token = _login(secured_client)
    assert isinstance(token, str) and len(token) > 10


def test_login_wrong_password_returns_401(secured_client):
    resp = secured_client.post(
        "/v1/auth/login", data={"username": "sectest", "password": "wrongpass"}
    )
    assert resp.status_code == 401


def test_protected_route_no_token_returns_401(secured_client):
    resp = secured_client.get("/v1/users")
    assert resp.status_code == 401


def test_protected_route_bad_token_returns_401(secured_client):
    resp = secured_client.get(
        "/v1/users", headers={"Authorization": "Bearer garbage.token.value"}
    )
    assert resp.status_code == 401


def test_protected_route_valid_token_returns_200(secured_client):
    token = _login(secured_client)
    resp = secured_client.get("/v1/users", headers=_bearer(token))
    assert resp.status_code == 200


# ── Rate limiting ─────────────────────────────────────────────────────────

def test_login_rate_limit_triggers_429(secured_client):
    """rate_limit_login_per_minute=3 → 4th request to /v1/auth/login is 429."""
    for _ in range(3):
        secured_client.post("/v1/auth/login", data={"username": "x", "password": "x"})
    resp = secured_client.post("/v1/auth/login", data={"username": "x", "password": "x"})
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many requests"


def test_general_rate_limit_triggers_429(secured_client):
    """rate_limit_per_minute=5 → 6th GET /v1/users in the same window is 429."""
    token = _login(secured_client)
    for _ in range(5):
        secured_client.get("/v1/users", headers=_bearer(token))
    resp = secured_client.get("/v1/users", headers=_bearer(token))
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many requests"
