import flet as ft


class Card(ft.Container):
    """A simple titled content card."""

    def __init__(self, title: str, body, **kwargs):
        body_control = body if isinstance(body, ft.Control) else ft.Text(str(body))
        super().__init__(
            content=ft.Column(
                [
                    ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                    body_control,
                ],
                spacing=10,
            ),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            **kwargs,
        )
