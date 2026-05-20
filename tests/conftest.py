"""
Shared test fixtures.

Read this file once and you'll know how every other test sets up its world:
- A FakePage stands in for ft.Page (doesn't render, just records).
- The event_bus / nav_service / router fixtures wire up a fresh app every test.
- The db_factory fixture provides an in-memory SQLite session factory.
"""
import pytest

from lib.core.events import EventBus
from lib.services.navigation_service import NavigationService
from lib.ui.router import FletRouter
from lib.database.session import SessionFactory
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
