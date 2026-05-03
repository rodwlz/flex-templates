import flet as ft
from lib.ui.components.nav_button import NavButton


class SideBar(ft.Container):
    """
    Left navigation panel.
    items: list of (label, route) tuples.
    """

    def __init__(self, items: list[tuple[str, str]], nav_service, width: int = 200):
        buttons = [
            NavButton(label, route, nav_service, width=width - 40)
            for label, route in items
        ]
        super().__init__(
            content=ft.Column(buttons, spacing=10),
            padding=20,
            width=width,
            bgcolor=ft.Colors.BLUE_GREY_900,
        )
