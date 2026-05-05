"""AdminCachesView: cache inspector dashboard."""
from unittest.mock import MagicMock
import flet as ft
import pytest

from lib.contracts.base import ActionResult
from lib.services.cache_registry import CacheRegistry
from lib.views.admin.caches import AdminCachesView
from tests.conftest import FakePage


@pytest.fixture(autouse=True)
def clean_registry():
    CacheRegistry._adapters = {}
    AdminCachesView._status_cache = {}
    yield
    CacheRegistry._adapters = {}
    AdminCachesView._status_cache = {}


def make_view(nav_service, route="/admin/caches"):
    page = FakePage(route)
    props = {"nav_service": nav_service}
    return AdminCachesView(page, props)


def test_view_renders_without_crashing(nav_service):
    rendered = make_view(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_view_shows_empty_state_when_no_caches(nav_service):
    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "No cache services registered" in rendered_str
    assert "REDIS_URL" in rendered_str


def test_view_shows_registered_adapter_alive(nav_service):
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"keys": ["a", "b", "c"]}
    )
    CacheRegistry.register("redis", adapter)

    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "REDIS" in rendered_str
    assert "3 keys" in rendered_str


def test_view_shows_failing_adapter_as_down(nav_service):
    adapter = MagicMock()
    adapter.execute.side_effect = ConnectionError("refused")
    CacheRegistry.register("redis_main", adapter)

    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    assert "REDIS_MAIN" in rendered_str
    assert "refused" in rendered_str


def test_view_lists_multiple_adapters_sorted(nav_service):
    a = MagicMock()
    a.execute.return_value = ActionResult(success=True, data={"keys": []})
    CacheRegistry.register("zeta", a)
    CacheRegistry.register("alpha", a)

    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    # Both should appear; alpha before zeta in row order.
    alpha_idx = rendered_str.find("ALPHA")
    zeta_idx = rendered_str.find("ZETA")
    assert 0 <= alpha_idx < zeta_idx


def test_view_has_correct_title():
    assert AdminCachesView.title == "Cache Inspector"


def test_view_shows_sidebar():
    assert AdminCachesView.show_sidebar is True


def test_view_includes_admin_tabs(nav_service):
    rendered = make_view(nav_service).render()
    rendered_str = str(rendered.controls)
    # Admin tabs render Databases + Caches labels.
    assert "Databases" in rendered_str
    assert "Caches" in rendered_str
