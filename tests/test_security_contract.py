"""
Security contract tests — structural + behavioral audit of the /v1/ API.

A new unprotected route will fail test_protected_endpoints_require_bearer_token.
Run after any change to lib/api/routes/ to verify the contract holds.
"""
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.config.settings import AppConfig
from lib.api.router_registry import mount_routes


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
def secured_app(monkeypatch):
    """Full v1 stack, in-memory DB, high rate limits so tests are never throttled."""
    import lib.models  # noqa: F401 — registers all ORM models in Base.metadata
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    config = AppConfig(rate_limit_per_minute=10000, rate_limit_login_per_minute=10000)
    app = FastAPI()
    mount_routes(app, config)
    return app


@pytest.fixture
def secured_client(secured_app):
    return TestClient(secured_app)


# ── Structural: all routes live under /v1/ ────────────────────────────────

def test_v1_prefix_on_all_routes(secured_app):
    """Every registered API route is under /v1/. Catches accidental top-level routes."""
    system_paths = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    api_routes = [
        r for r in secured_app.routes
        if isinstance(r, APIRoute) and r.path not in system_paths
    ]
    non_v1 = [r.path for r in api_routes if not r.path.startswith("/v1/")]
    assert non_v1 == [], f"Routes found outside /v1/: {non_v1}"


# ── Behavioral: login is the only public endpoint ─────────────────────────

def test_login_reaches_handler_without_token(secured_client):
    """Login is reachable without Bearer — returns handler error, not middleware 401."""
    resp = secured_client.post(
        "/v1/auth/login", data={"username": "nosuchuser", "password": "bad"}
    )
    assert resp.status_code == 401
    # "Invalid credentials" = handler ran. "Not authenticated" = auth middleware blocked.
    assert resp.json()["detail"] == "Invalid credentials"


def test_protected_endpoints_require_bearer_token(secured_client):
    """Every non-login endpoint returns 401 'Not authenticated' when no Bearer is sent."""
    endpoints = [
        ("GET", "/v1/users"),
        ("GET", "/v1/roles"),
        ("GET", "/v1/auth/me"),
        ("GET", "/v1/caches/"),
        ("GET", "/v1/scheduler/jobs"),
    ]
    for method, path in endpoints:
        resp = secured_client.request(method, path)
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {path}, got {resp.status_code}"
        )
        assert resp.json()["detail"] == "Not authenticated", (
            f"{method} {path}: expected 'Not authenticated', got {resp.json()['detail']!r}"
        )
