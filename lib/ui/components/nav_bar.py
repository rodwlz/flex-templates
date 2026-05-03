import flet as ft
from lib.contracts.base import ActionRequest


class NavBar(ft.AppBar):
    """Top app bar with title and optional back arrow."""

    def __init__(self, title: str, nav_service, show_back: bool = True):
        leading = None
        if show_back and nav_service.can_go_back:
            leading = ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: nav_service.execute(ActionRequest(action="back")),
            )

        super().__init__(
            leading=leading,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
