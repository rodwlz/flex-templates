"""
Smoke tests — the 'is anything fundamentally broken?' safety net.

Run these after any change.  If they all pass, the app at least *boots*.
If they fail, the failure message tells you which route or import broke.
"""
import importlib

import pytest

from tests.conftest import FakePage


# Every URL the app should know how to render.
ALL_ROUTES = [
    "/",
    "/login",
    "/products",
    "/products/1",
    "/products/2?tab=stock",
    "/this-is-an-unknown-page",
]


@pytest.fixture
def configured_router(router):
    """Same router, but with the parameterized routes from main.py registered."""
    router.register("/products/{id}", "lib.views.product_detail")
    return router


@pytest.mark.parametrize("url", ALL_ROUTES)
def test_route_renders_without_errors(configured_router, url):
    """If this fails, your app won't load. Check the traceback for the broken view."""
    page = FakePage(url)
    configured_router.route_change(page)

    assert len(page.views) == 1, f"No view rendered for {url!r}"
    assert page.update_count == 1


def test_main_module_imports_cleanly():
    """If `python main.py` gives an ImportError, this catches it."""
    importlib.import_module("main")


@pytest.mark.parametrize(
    "module_path",
    [
        "lib.contracts.base",
        "lib.core.events",
        "lib.core.interfaces",
        "lib.services.navigation_service",
        "lib.services.nav",
        "lib.security.crypto",
        "lib.security.vault_store",
        "lib.security.vault_service",
        "lib.ui.adapter",
        "lib.ui.router",
        "lib.ui.layouts.base_view",
        "lib.ui.components.dev_nav",
        "lib.ui.components.nav_button",
        "lib.ui.components.back_button",
        "lib.ui.components.nav_bar",
        "lib.ui.components.side_bar",
        "lib.ui.components.card",
        "lib.ui.components.copy_button",
        "lib.views.home",
        "lib.views.login",
        "lib.views.products",
        "lib.views.product_detail",
        "lib.views.security",
        "lib.views.vault_test",
        "lib.views.not_found",
    ],
)
def test_module_imports_cleanly(module_path):
    """Every lib module should be importable in isolation."""
    importlib.import_module(module_path)
