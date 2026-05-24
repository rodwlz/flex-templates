"""Login view — entry point for admin config.

Uses backend.login() (ServiceBackendAdapter today, HttpBackendAdapter tomorrow).
Swap the adapter in main.py — this file does not change.
"""
import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.back_button import BackButton


class LoginView(BaseView):
    title = "Login"
    show_sidebar = False

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._error_text: ft.Text | None = None
        self._username_field: ft.TextField | None = None
        self._password_field: ft.TextField | None = None

    def _on_sign_out(self, _e):
        if self._backend is not None:
            self._backend.auth.logout()
        self.nav_service.execute(ActionRequest(action="visit", data={"url": "/"}))

    def _on_sign_in(self, _e):
        username = self._username_field.value.strip()
        password = self._password_field.value.strip()

        if not username or not password:
            self._error_text.value = "Username and password are required."
            self.page.update()
            return

        if self._backend is None:
            self._error_text.value = "Backend not available."
            self.page.update()
            return

        try:
            self._backend.auth.login(username, password)
            self.nav_service.execute(
                ActionRequest(action="visit", data={"url": "/manage/users"})
            )
        except ValueError:
            self._error_text.value = "Invalid username or password."
            self.page.update()

    def build_content(self):
        if self._backend is not None and self._backend.auth.current_user() is not None:
            user = self._backend.auth.current_user()
            return ft.Column(
                [
                    ft.Text("Already signed in", size=28, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"Logged in as: {user.get('username', 'unknown')}",
                        color=ft.Colors.BLUE_GREY_300,
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                content=ft.Text("Go to Home"),
                                on_click=lambda _: self.nav_service.execute(
                                    ActionRequest(action="visit", data={"url": "/"})
                                ),
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("Sign out"),
                                on_click=self._on_sign_out,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=15,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            )

        self._username_field = ft.TextField(label="Username", width=320, autofocus=True)
        self._password_field = ft.TextField(
            label="Password", password=True, can_reveal_password=True, width=320
        )
        self._error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

        return ft.Column(
            [
                ft.Text("Sign In", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("FlexTemplates admin config", size=13, color=ft.Colors.BLUE_GREY_300),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self._username_field,
                self._password_field,
                self._error_text,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("Sign In"),
                            width=150,
                            on_click=self._on_sign_in,
                        ),
                        BackButton(self.nav_service),
                    ],
                    spacing=10,
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return LoginView(page, props).render()
