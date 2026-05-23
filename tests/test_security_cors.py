"""CORS policy — Access-Control header tests for allowed and blocked origins."""
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.config.settings import AppConfig
from lib.api.router_registry import mount_routes

_ALLOWED = "http://localhost:3000"
_BLOCKED = "https://evil.com"


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
def cors_client(monkeypatch):
    """App with CORS configured to allow _ALLOWED only."""
    import lib.models  # noqa: F401
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    config = AppConfig(
        cors_origins=_ALLOWED,
        rate_limit_per_minute=10000,
        rate_limit_login_per_minute=10000,
    )
    app = FastAPI()
    origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    mount_routes(app, config)
    return TestClient(app, raise_server_exceptions=False)


def test_cors_allows_configured_origin(cors_client):
    """Preflight from an allowed origin returns the origin in the response header."""
    resp = cors_client.options(
        "/v1/auth/login",
        headers={"Origin": _ALLOWED, "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers.get("access-control-allow-origin") == _ALLOWED


def test_cors_blocks_unknown_origin(cors_client):
    """Preflight from an unknown origin does not echo that origin back."""
    resp = cors_client.options(
        "/v1/auth/login",
        headers={"Origin": _BLOCKED, "Access-Control-Request-Method": "POST"},
    )
    origin_header = resp.headers.get("access-control-allow-origin", "")
    assert origin_header != _BLOCKED


def test_cors_credentials_allowed(cors_client):
    """Preflight response includes Access-Control-Allow-Credentials: true."""
    resp = cors_client.options(
        "/v1/auth/login",
        headers={"Origin": _ALLOWED, "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers.get("access-control-allow-credentials") == "true"
