"""
Dev-only browser-style URL bar. Always visible at the top of every page.

Layout: [←] [→] [URL field] [Go] [history dropdown]
        Type any URL and press Enter (or Go) to jump to it.

Enable in main.py:
    router.set_props_factory(lambda: {
        "nav_service": nav_service,
        "dev_nav": True,
    })

Remove "dev_nav" key (or set to False) before shipping.
"""
import flet as ft

from lib.contracts.base import ActionRequest
from lib.services.navigation_service import NavigationService


class DevNav:
    def __init__(self, nav_service: NavigationService, page: ft.Page):
        self._nav = nav_service
        self._page = page
        self._field = ft.TextField(
            value=nav_service.current,
            expand=True,
            dense=True,
            border_radius=20,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=6),
            text_size=13,
            on_submit=self._go,
        )

    # ── Actions ────────────────────────────────────────────────────────────

    def _go(self, _e=None) -> None:
        url = (self._field.value or "").strip()
        if url:
            self._nav.execute(ActionRequest(action="visit", data={"url": url}))

    def _back(self, _e=None) -> None:
        self._nav.execute(ActionRequest(action="back"))

    def _forward(self, _e=None) -> None:
        self._nav.execute(ActionRequest(action="forward"))

    def _jump(self, url: str) -> None:
        self._nav.execute(ActionRequest(action="visit", data={"url": url}))

    # ── History dropdown ───────────────────────────────────────────────────

    def _history_menu(self) -> ft.PopupMenuButton:
        def label(text: str) -> ft.Text:
            return ft.Text(text, size=13)

        items: list[ft.PopupMenuItem] = []

        if self._nav.back_stack[:-1]:
            items.append(ft.PopupMenuItem(content=label("── Back ──"), disabled=True))
            for url in reversed(self._nav.back_stack[:-1]):
                items.append(
                    ft.PopupMenuItem(content=label(url), on_click=lambda e, u=url: self._jump(u))
                )

        items.append(ft.PopupMenuItem(content=label(f"● {self._nav.current}"), disabled=True))

        if self._nav.forward_stack:
            items.append(ft.PopupMenuItem(content=label("── Forward ──"), disabled=True))
            for url in self._nav.forward_stack:
                items.append(
                    ft.PopupMenuItem(content=label(url), on_click=lambda e, u=url: self._jump(u))
                )

        return ft.PopupMenuButton(icon=ft.Icons.HISTORY, items=items, tooltip="History")

    # ── Render ─────────────────────────────────────────────────────────────

    def build(self) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ARROW_BACK,
                        on_click=self._back,
                        disabled=not self._nav.can_go_back,
                        tooltip="Back",
                    ),
                    ft.IconButton(
                        ft.Icons.ARROW_FORWARD,
                        on_click=self._forward,
                        disabled=not self._nav.can_go_forward,
                        tooltip="Forward",
                    ),
                    self._field,
                    ft.IconButton(ft.Icons.SEND, on_click=self._go, tooltip="Go"),
                    self._history_menu(),
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE))),
        )
