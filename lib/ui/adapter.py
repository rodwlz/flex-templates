import flet as ft
from lib.contracts.base import Event
from lib.core.interfaces import INavigationAdapter
from lib.services.navigation_service import NavigationService


class FletNavigationAdapter(INavigationAdapter):
    """
    Bridges NavigationService events → Flet page.go().
    Only this file is allowed to call page.go() for navigation.
    """

    def __init__(self, navigation_service: NavigationService):
        self._page: ft.Page | None = None
        navigation_service._event_bus.subscribe("nav.route_changed", self._on_route_changed)

    def bind_page(self, page: ft.Page) -> None:
        """Call once when the Flet app starts, before any navigation."""
        self._page = page

    # ── INavigationAdapter ─────────────────────────────────────────────────

    def navigate_to(self, url: str) -> None:
        if self._page:
            self._page.go(url)

    def get_current_route(self) -> str:
        return self._page.route if self._page else "/"

    # ── Event handler ──────────────────────────────────────────────────────

    def _on_route_changed(self, event: Event) -> None:
        if self._page:
            url = event.payload["url"]
            # Only call page.go if Flet doesn't already know about this URL.
            # This prevents double-navigation when Flet itself triggered the change.
            if self._page.route != url:
                self._page.go(url)
