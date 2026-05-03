import importlib
import re
from types import ModuleType
from typing import Callable
from urllib.parse import urlparse, parse_qs
import flet as ft

from lib.services.navigation_service import NavigationService
from lib.contracts.base import ActionRequest


class FletRouter:
    """
    URL → view loader for Flet.

    Convention (zero config):
        /login       → flex_app.views.login.view(page, props)
        /            → flex_app.views.home.view(page, props)
        /not_found   → flex_app.views.not_found.view(page, props)  (404 fallback)

    Named routes (explicit, for parameterized URLs):
        router.register("/users/{id}", "flex_app.views.user_detail")
        → /users/42  passes props["params"] = {"id": "42"}

    Props:
        Every view receives a props dict from set_props_factory().
        props["params"] is always present (empty dict if no URL params).
    """

    def __init__(
        self,
        navigation_service: NavigationService,
        views_package: str = "flex_app.views",
    ):
        self._nav_service = navigation_service
        self._views_package = views_package
        self._cache: dict[str, ModuleType] = {}
        self._named_routes: list[tuple[re.Pattern, str]] = []
        self._props_factory: Callable[[], dict] = lambda: {}

    # ── Configuration ──────────────────────────────────────────────────────

    def register(self, pattern: str, module_path: str) -> "FletRouter":
        """
        Register a parameterized route.
        Pattern syntax: /users/{id}  or  /reports/{year}/{month}
        Returns self so calls can be chained.
        """
        regex = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern)
        self._named_routes.append((re.compile(f"^{regex}$"), module_path))
        return self

    def set_props_factory(self, factory: Callable[[], dict]) -> None:
        """
        Provide a function that returns the services/deps for every view.
        Called fresh on every route change so factories are always current.

        Example:
            router.set_props_factory(lambda: {
                "user_service": container.user_service(),
                "nav_service": container.navigation_service(),
            })
        """
        self._props_factory = factory

    # ── Flet entry point ───────────────────────────────────────────────────

    def route_change(self, page: ft.Page) -> None:
        """
        Wire this to ft.app(on_route_change=router.route_change).
        Also tells NavigationService about the new URL so history stays in sync
        when the user navigates via browser back/forward or direct URL entry.
        """
        raw = page.route or "/"
        parsed = urlparse(raw)
        path = parsed.path or "/"
        query = {
            k: (v[0] if len(v) == 1 else v)
            for k, v in parse_qs(parsed.query).items()
        }

        page.views.clear()

        # Keep NavigationService history in sync with Flet's URL bar.
        self._nav_service.execute(ActionRequest(action="visit", data={"url": raw}))

        view = self._resolve(path, page, query)
        page.views.append(view)
        page.update()

    def view_pop(self, page: ft.Page) -> None:
        """Wire to ft.app(on_view_pop=router.view_pop) for hardware back button."""
        page.views.pop()
        if page.views:
            page.go(page.views[-1].route)

    # ── Resolution ─────────────────────────────────────────────────────────

    def _resolve(self, path: str, page: ft.Page, query: dict) -> ft.View:
        # 1. Check named/parameterized routes first (most specific wins).
        for pattern, module_path in self._named_routes:
            match = pattern.match(path)
            if match:
                return self._load_view(module_path, page, match.groupdict(), query)

        # 2. Convention-based: /login → views.login, / → views.home
        module_path = self._url_to_module(path)
        try:
            return self._load_view(module_path, page, {}, query)
        except ModuleNotFoundError:
            return self._load_view(
                f"{self._views_package}.not_found", page, {"url": path}, query
            )

    def _url_to_module(self, url: str) -> str:
        if url in ("/", ""):
            return f"{self._views_package}.home"
        # /admin/users → views.admin.users
        segment = url.strip("/").replace("/", ".")
        return f"{self._views_package}.{segment}"

    # ── View loading ───────────────────────────────────────────────────────

    def _load_view(
        self, module_path: str, page: ft.Page, params: dict, query: dict
    ) -> ft.View:
        mod = self._get_module(module_path)

        if not hasattr(mod, "view"):
            raise AttributeError(
                f"{module_path} must define a top-level view(page, props) function"
            )

        props = self._props_factory()
        props["params"] = params
        props["query"] = query

        return mod.view(page, props)

    def _get_module(self, module_path: str) -> ModuleType:
        if module_path not in self._cache:
            self._cache[module_path] = importlib.import_module(module_path)
        return self._cache[module_path]

    def invalidate_cache(self, module_path: str | None = None) -> None:
        """Clear one cached module or the entire cache (useful in dev/hot-reload)."""
        if module_path:
            self._cache.pop(module_path, None)
        else:
            self._cache.clear()
