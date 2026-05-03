import flet as ft
from lib.core.interfaces import IErrorAdapter


class FletErrorAdapter(IErrorAdapter):
    """
    IErrorAdapter implementation for Flet.

    Warning (fatal=False) → SnackBar at the bottom of the screen.
    Fatal (fatal=True)    → replaces all views with a full-screen error page.
    """

    def __init__(self):
        self._page: ft.Page | None = None

    def bind_page(self, page: ft.Page) -> None:
        self._page = page

    def show_error(self, message: str, fatal: bool = False) -> None:
        if self._page is None:
            return
        if fatal:
            self._page.views.clear()
            self._page.views.append(ft.View(
                route="/error",
                controls=[
                    ft.Column(
                        [
                            ft.Text("Something went wrong", size=24,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text(message, color=ft.Colors.RED_400),
                            ft.ElevatedButton(
                                content=ft.Text("Go Home"),
                                on_click=lambda _: self._page.go("/"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    )
                ],
            ))
        else:
            self._page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ORANGE_700,
            )
            self._page.snack_bar.open = True
        self._page.update()
