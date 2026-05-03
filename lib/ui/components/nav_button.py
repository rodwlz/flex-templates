import flet as ft
from lib.contracts.base import ActionRequest


class NavButton(ft.ElevatedButton):
    """A button that navigates to a route via NavigationService."""

    def __init__(self, label: str, route: str, nav_service, **kwargs):
        super().__init__(
            content=label,
            on_click=lambda _: nav_service.execute(
                ActionRequest(action="visit", data={"url": route})
            ),
            **kwargs,
        )
