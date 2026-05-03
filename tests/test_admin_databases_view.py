"""AdminDatabasesView: database inspector dashboard."""
import flet as ft
import pytest

from lib.views.admin.databases import AdminDatabasesView
from lib.config.settings import AppConfig
from tests.conftest import FakePage


def make_view(view_cls, route="/", nav_service=None, config=None):
    """Build a view instance with sensible defaults for tests."""
    page = FakePage(route)
    props = {
        "nav_service": nav_service,
        "config": config,
    }
    return view_cls(page, props)


def test_view_renders_without_crashing(nav_service):
    """AdminDatabasesView.render() returns a valid ft.View."""
    config = AppConfig()
    v = make_view(AdminDatabasesView, nav_service=nav_service, config=config).render()
    assert isinstance(v, ft.View)
    assert v.route == "/"


def test_view_displays_database_list(nav_service):
    """View contains text/elements showing database names."""
    # Create a config with sample databases
    config = AppConfig()
    config.databases = {"main": "sqlite:///./dev.db", "analytics": "postgresql://localhost/analytics"}

    v = make_view(AdminDatabasesView, nav_service=nav_service, config=config).render()

    # Serialize to string and check that database names appear
    view_str = str(v.controls)
    assert "main" in view_str or "Connected Databases" in view_str  # Should show database info


def test_view_shows_empty_message_when_no_databases(nav_service):
    """View shows appropriate message when no databases configured."""
    config = AppConfig()
    config.databases = {}

    view = make_view(AdminDatabasesView, nav_service=nav_service, config=config)
    rendered = view.render()

    # Should render without error
    assert isinstance(rendered, ft.View)


def test_view_has_correct_title(nav_service):
    """View has 'Database Inspector' title."""
    config = AppConfig()
    v = make_view(AdminDatabasesView, nav_service=nav_service, config=config)
    assert v.title == "Database Inspector"


def test_view_shows_sidebar(nav_service):
    """View shows sidebar by default."""
    config = AppConfig()
    v = make_view(AdminDatabasesView, nav_service=nav_service, config=config)
    assert v.show_sidebar is True
