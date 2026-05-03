"""
Shared test fixtures.

Read this file once and you'll know how every other test sets up its world:
- A FakePage stands in for ft.Page (doesn't render, just records).
- The event_bus / nav_service / router fixtures wire up a fresh app every test.
"""
import pytest

from lib.core.events import EventBus
from lib.services.navigation_service import NavigationService
from lib.ui.router import FletRouter


class FakePage:
    """Stand-in for ft.Page. Records what would have happened without rendering."""

    def __init__(self, route: str = "/"):
        self.route = route
        self.views = []
        self.update_count = 0

    def update(self):
        self.update_count += 1

    def go(self, url: str):
        self.route = url


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
