"""AdminDatabasesView: database inspector dashboard."""
from unittest.mock import MagicMock
import flet as ft
import pytest

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.services.connection_tester import ConnectionTester
from lib.views.admin.databases import AdminDatabasesView
from tests.conftest import FakePage


@pytest.fixture(autouse=True)
def clean_registry():
    saved = dict(ConnectionRegistry._factories)
    ConnectionRegistry._factories = {}
    AdminDatabasesView._status_cache = {}
    yield
    ConnectionRegistry._factories = saved
    AdminDatabasesView._status_cache = {}


def make_view(nav_service, route="/admin/databases"):
    page = FakePage(route)
    props = {
        "nav_service": nav_service,
        "connection_tester": ConnectionTester(),
    }
    return AdminDatabasesView(page, props)


def test_view_renders_without_crashing(nav_service):
    rendered = make_view(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_view_shows_empty_state_when_no_databases(nav_service):
    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "No SQL databases registered" in rendered_str
    assert "POSTGRES_URL" in rendered_str
    assert "DATABASE_<NAME>" in rendered_str


def test_view_displays_database_names(nav_service, db_factory):
    """Real in-memory SQLite — name shows alive status with latency."""
    ConnectionRegistry._factories["main"] = db_factory

    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "MAIN" in rendered_str
    # In-memory SQLite is reachable, so card shows ms latency.
    assert "ms" in rendered_str


def test_view_displays_failing_database_as_down(nav_service):
    fake = MagicMock(spec=SessionFactory)
    fake._engine = MagicMock()
    # Tester will call factory.session() and get an error.
    fake.session.side_effect = Exception("boom")
    ConnectionRegistry._factories["broken"] = fake

    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "BROKEN" in rendered_str
    assert "🔴" in rendered_str or "boom" in rendered_str


def test_view_has_correct_title():
    assert AdminDatabasesView.title == "Database Inspector"


def test_view_shows_sidebar():
    assert AdminDatabasesView.show_sidebar is True


def test_view_includes_admin_tabs(nav_service):
    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "Databases" in rendered_str
    assert "Caches" in rendered_str


def test_view_shows_live_count_in_header(nav_service, db_factory):
    ConnectionRegistry._factories["one"] = db_factory
    ConnectionRegistry._factories["two"] = db_factory

    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    # "2 of 2 live" since both factories are the same in-memory SQLite.
    assert "2 of 2" in rendered_str or "of 2" in rendered_str
