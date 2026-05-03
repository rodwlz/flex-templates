"""Thin wrapper around NavigationService with a clean method API.

Usage in views / services (nav is in props):
    self.nav.go("/login")
    self.nav.back()
    self.nav.forward()
    print(self.nav.current)
"""
from lib.contracts.base import ActionRequest
from lib.services.navigation_service import NavigationService


class Nav:
    """Simple interface over NavigationService. No ActionRequest boilerplate."""

    def __init__(self, service: NavigationService):
        self._service = service

    def go(self, url: str) -> None:
        """Navigate to *url*, pushing it onto the history stack."""
        self._service.execute(ActionRequest(action="visit", data={"url": url}))

    def back(self, steps: int = 1) -> bool:
        """Go back *steps* pages. Returns False if there is no history."""
        result = self._service.execute(
            ActionRequest(action="back", data={"steps": steps})
        )
        return result.success

    def forward(self, steps: int = 1) -> bool:
        """Go forward *steps* pages. Returns False if there is no forward history."""
        result = self._service.execute(
            ActionRequest(action="forward", data={"steps": steps})
        )
        return result.success

    def clear(self) -> None:
        """Reset history — keeps current page, drops back/forward stacks."""
        self._service.execute(ActionRequest(action="clear"))

    @property
    def current(self) -> str:
        """URL of the currently active page."""
        return self._service.current

    @property
    def can_go_back(self) -> bool:
        return self._service.can_go_back

    @property
    def can_go_forward(self) -> bool:
        return self._service.can_go_forward
