import flet as ft

from lib.ui.layouts.base_view import BaseView
from lib.ui.components.nav_button import NavButton


class NotFoundView(BaseView):
    title = "Not Found"

    def build_content(self):
        url = self.props.get("params", {}).get("url", "unknown")
        return ft.Column(
            [
                ft.Text("404", size=64, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                ft.Text(f"Page not found: {url}"),
                NavButton("Go Home", "/", self.nav_service),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return NotFoundView(page, props).render()
