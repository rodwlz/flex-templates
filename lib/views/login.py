import flet as ft

from lib.ui.layouts.base_view import BaseView
from lib.ui.components.back_button import BackButton


class LoginView(BaseView):
    title = "Login"
    show_sidebar = False  # login is "outside" the app — no sidebar

    def build_content(self):
        return ft.Column(
            [
                ft.Text("Login", size=28, weight=ft.FontWeight.BOLD),
                ft.TextField(label="Username", width=320),
                ft.TextField(
                    label="Password", password=True, can_reveal_password=True, width=320
                ),
                ft.Row(
                    [
                        ft.ElevatedButton("Sign In", width=150),
                        BackButton(self.nav_service),
                    ],
                    spacing=10,
                ),
            ],
            spacing=15,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return LoginView(page, props).render()
