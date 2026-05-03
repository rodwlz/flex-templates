import flet as ft
from lib.contracts.base import ActionRequest


class BackButton(ft.TextButton):
    """A button that goes to the previous page in nav history."""

    def __init__(self, nav_service, label: str = "← Back", **kwargs):
        super().__init__(
            content=label,
            on_click=lambda _: nav_service.execute(ActionRequest(action="back")),
            **kwargs,
        )
