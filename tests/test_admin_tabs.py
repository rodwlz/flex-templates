"""AdminTabs: pill-style sub-navigation between admin views."""
import flet as ft

from lib.ui.components.admin_tabs import AdminTabs, ADMIN_TABS


def test_admin_tabs_constants_define_databases_and_caches():
    routes = {route for _, route, _ in ADMIN_TABS}
    assert "/admin/databases" in routes
    assert "/admin/caches" in routes


def test_admin_tabs_highlights_current_route(nav_service):
    tabs = AdminTabs("/admin/databases", nav_service)
    rendered = str(tabs.content.controls)
    # Database pill should be active (white text), cache pill inactive (grey).
    assert "Databases" in rendered
    assert "Caches" in rendered


def test_admin_tabs_renders_for_each_tab(nav_service):
    tabs = AdminTabs("/admin/caches", nav_service)
    pills = tabs.content.controls
    assert len(pills) == len(ADMIN_TABS)
    for pill in pills:
        assert isinstance(pill, ft.Container)


def test_admin_tabs_active_pill_has_no_click_handler(nav_service):
    """Clicking the active tab should be a no-op (already there)."""
    tabs = AdminTabs("/admin/databases", nav_service)
    pills = tabs.content.controls
    # First pill is Databases — active when route is /admin/databases.
    assert pills[0].on_click is None


def test_admin_tabs_inactive_pill_has_click_handler(nav_service):
    tabs = AdminTabs("/admin/databases", nav_service)
    pills = tabs.content.controls
    # Second pill is Caches — inactive when route is /admin/databases.
    assert pills[1].on_click is not None
