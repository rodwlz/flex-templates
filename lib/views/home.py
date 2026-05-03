import flet as ft

from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.nav_button import NavButton


class HomeView(BaseView):
    title = "Home"

    def build_content(self):
        return ft.Column(
            [
                ft.Text("Welcome to FlexTemplates", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Click the buttons in the sidebar or below to navigate."),
                ft.Row(
                    [
                        NavButton("Open Login", "/login", self.nav_service),
                        NavButton("Browse Products", "/products", self.nav_service),
                    ],
                    spacing=10,
                ),
                Card(
                    title="What is this?",
                    body="A modular Flet + FastAPI template. Every layer talks "
                    "through Pydantic contracts, so you can swap pieces without "
                    "breaking anything else.",
                ),
            ],
            spacing=20,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return HomeView(page, props).render()
