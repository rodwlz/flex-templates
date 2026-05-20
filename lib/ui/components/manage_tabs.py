"""Manage section sub-navigation — pill-style tabs for /manage/ views."""
from __future__ import annotations

import flet as ft

from lib.contracts.base import ActionRequest


MANAGE_TABS: list[tuple[str, str, str]] = [
    ("Users", "/manage/users", ft.Icons.PEOPLE),
    ("Roles", "/manage/roles", ft.Icons.VERIFIED_USER),
]


class ManageTabs(ft.Container):
    """Horizontal pill bar linking between /manage/ views.

    Highlights the tab matching *current_route*.
    """

    def __init__(self, current_route: str, nav_service):
        pills = [
            self._pill(label, route, icon, current_route, nav_service)
            for label, route, icon in MANAGE_TABS
        ]
        super().__init__(
            content=ft.Row(pills, spacing=8),
            padding=ft.padding.only(bottom=20),
        )

    @staticmethod
    def _pill(label: str, route: str, icon, current_route: str, nav_service) -> ft.Container:
        active = current_route == route
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=ft.Colors.WHITE if active else ft.Colors.BLUE_GREY_300),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL,
                        color=ft.Colors.WHITE if active else ft.Colors.BLUE_GREY_300,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor=ft.Colors.BLUE_700 if active else ft.Colors.BLUE_GREY_800,
            border_radius=20,
            on_click=None if active else (
                lambda _e, r=route: nav_service.execute(
                    ActionRequest(action="visit", data={"url": r})
                )
            ),
        )
