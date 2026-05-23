"""
Shared test fixtures.

Read this file once and you'll know how every other test sets up its world:
- A FakePage stands in for ft.Page (doesn't render, just records).
- The event_bus / nav_service / router fixtures wire up a fresh app every test.
- The db_factory fixture provides an in-memory SQLite session factory.
"""
import os

# Seed JWT_SECRET_KEY from .secrets/.env before jwt_handler is imported.
# jwt_handler reads the key at module-import time, so this must run at
# conftest module level, not inside a fixture. Only JWT_SECRET_KEY is injected
# to avoid polluting VAULT_MASTER_KEY / VAULT_CONFIRM_KEY, which vault tests
# manage independently via tmp_path.
try:
    from dotenv import dotenv_values
    _secrets = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".secrets", ".env"))
    if "JWT_SECRET_KEY" in _secrets and not os.getenv("JWT_SECRET_KEY"):
        os.environ["JWT_SECRET_KEY"] = _secrets["JWT_SECRET_KEY"]
except Exception:
    pass  # file missing or dotenv unavailable — warning will still fire

import pytest

from lib.core.events import EventBus
from lib.services.navigation_service import NavigationService
from lib.ui.router import FletRouter
from lib.database.session import SessionFactory, ConnectionRegistry
from lib.database.base import Base
import lib.models  # noqa: F401 — ensures all ORM models are registered in Base.metadata
from lib.repositories.user_repository import UserRepository


class FakePage:
    """Stand-in for ft.Page. Records what would have happened without rendering."""

    def __init__(self, route: str = "/"):
        self.route = route
        self.views = []
        self.overlay = []
        self.update_count = 0

    def update(self):
        self.update_count += 1

    def go(self, url: str):
        self.route = url

    def run_task(self, coro_fn, *args, **kwargs):
        """Run async tasks synchronously so test assertions see the result."""
        import asyncio
        asyncio.run(coro_fn(*args, **kwargs))


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def nav_service(event_bus):
    return NavigationService(event_bus)


@pytest.fixture
def router(nav_service):
    r = FletRouter(nav_service, views_package="lib.views")
    r.set_props_factory(lambda: {"nav_service": nav_service})
    return r


@pytest.fixture
def fake_page():
    return FakePage()


@pytest.fixture
def db_factory():
    factory = SessionFactory("sqlite:///:memory:")
    factory.create_tables(Base)
    return factory


@pytest.fixture
def user_repo(db_factory):
    return UserRepository(db_factory)


# ── HTTP adapter test infrastructure ─────────────────────────────────────────

from sqlalchemy.pool import StaticPool


def _http_mem_factory() -> SessionFactory:
    """In-memory SQLite that keeps one connection alive (for HTTP adapter tests)."""
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = __import__('sqlalchemy').create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = __import__('sqlalchemy.orm', fromlist=['sessionmaker']).sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def http_factory(monkeypatch):
    """In-memory DB registered as 'postgres' — shared by http_backend + test_user."""
    factory = _http_mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )
    return factory


def _v1_app(*routers):
    """
    Build a test FastAPI app serving the given routers under /v1/ with no
    rate limiting or auth enforcement. Preserves /v1/... URL patterns after
    route modules dropped their /v1 prefix.
    """
    from fastapi import FastAPI, APIRouter
    v1 = APIRouter(prefix="/v1")
    for r in routers:
        v1.include_router(r)
    app = FastAPI()
    app.include_router(v1)
    return app


@pytest.fixture
def http_app(http_factory):
    """FastAPI app with all v1 routes — used by http_backend fixture."""
    from lib.api.routes import (
        auth as auth_routes,
        users as users_routes,
        roles as roles_routes,
        scheduler as scheduler_routes,
    )
    return _v1_app(
        auth_routes.router,
        users_routes.router,
        roles_routes.router,
        scheduler_routes.router,
    )


@pytest.fixture
def http_backend(http_app):
    """HttpBackendAdapter wired to the in-memory test FastAPI app."""
    from fastapi.testclient import TestClient
    from lib.adapters.http_backend_adapter import HttpBackendAdapter
    client = TestClient(http_app)
    return HttpBackendAdapter(base_url="http://testserver", _client=client)


@pytest.fixture
def test_user(http_factory):
    """Create a real user in the test DB; returns {username, password, email}."""
    from lib.services.user_service import UserService
    svc = UserService(http_factory)
    svc.create_user(username="testuser", email="test@example.com", password="testpass123")
    return {"username": "testuser", "password": "testpass123", "email": "test@example.com"}
