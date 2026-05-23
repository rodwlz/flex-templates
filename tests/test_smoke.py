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
    "/manage/users",
    "/manage/roles",
    "/admin/scheduler",
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
        "lib.config.settings",
        "lib.config.cli",
        "lib.contracts.base",
        "lib.contracts.view_context",
        "lib.core.events",
        "lib.core.interfaces",
        "lib.database.base",
        "lib.database.session",
        "lib.database.query",
        "lib.database.uow",
        "lib.models.user",
        "lib.repositories.base",
        "lib.repositories.user_repository",
        "lib.adapters.redis_adapter",
        "lib.adapters.file_adapter",
        "lib.services.navigation_service",
        "lib.services.nav",
        "lib.services.schema_inspector",
        "lib.services.connection_tester",
        "lib.services.cache_registry",
        "lib.services.cache_tester",
        "lib.security.crypto",
        "lib.security.vault_store",
        "lib.security.vault_service",
        "lib.api.server",
        "lib.api.mount_service",
        "lib.api.router_registry",
        "lib.api.rate_limiter",
        "lib.api.v1",
        "lib.auth.jwt_handler",
        "lib.auth.dependencies",
        "lib.api.routes.auth",
        "lib.api.routes.users",
        "lib.api.routes.caches",
        "lib.middleware.logging",
        "lib.tasks.scheduler",
        "lib.ui.adapter",
        "lib.ui.error_adapter",
        "lib.ui.router",
        "lib.ui.layouts.base_view",
        "lib.ui.components.dev_nav",
        "lib.ui.components.nav_button",
        "lib.ui.components.back_button",
        "lib.ui.components.nav_bar",
        "lib.ui.components.side_bar",
        "lib.ui.components.card",
        "lib.ui.components.copy_button",
        "lib.ui.components.admin_tabs",
        "lib.ui.components.status_card",
        "lib.adapters.backend_adapter",
        "lib.adapters._utils",
        "lib.adapters.auth_adapter",
        "lib.adapters.users_adapter",
        "lib.adapters.roles_adapter",
        "lib.adapters.scheduler_adapter",
        "lib.adapters.http_session",
        "lib.adapters.http_auth_adapter",
        "lib.adapters.http_users_adapter",
        "lib.adapters.http_roles_adapter",
        "lib.adapters.http_scheduler_adapter",
        "lib.adapters.http_backend_adapter",
        "lib.api.routes.scheduler",
        "lib.ui.layouts.protected_view",
        "lib.ui.components.manage_tabs",
        "lib.views.home",
        "lib.views.login",
        "lib.views.products",
        "lib.views.product_detail",
        "lib.views.security",
        "lib.views.vault_test",
        "lib.views.not_found",
        "lib.views.admin.databases",
        "lib.views.admin.caches",
        "lib.views.manage.users",
        "lib.views.manage.roles",
        "lib.views.admin.scheduler",
    ],
)
def test_module_imports_cleanly(module_path):
    """Every lib module should be importable in isolation."""
    importlib.import_module(module_path)
