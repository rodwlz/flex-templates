"""Admin database inspector view — live status for every registered SQL database."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import flet as ft

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.ui.components.admin_tabs import AdminTabs
from lib.ui.components.status_card import StatusCard
from lib.ui.layouts.protected_view import ProtectedView


class AdminDatabasesView(ProtectedView):
    """Database inspector dashboard — pings each registered SQL connection."""

    title = "Database Inspector"
    show_sidebar = True

    # Persists across navigation — cleared only by the Refresh button.
    _status_cache: dict[str, tuple[bool, float | None, str | None]] = {}

    # ── Connection probing ─────────────────────────────────────────────────
    def _probe(self, db_name: str) -> tuple[bool, float | None, str | None]:
        result = self.props["connection_tester"].execute(
            ActionRequest(action="test", data={"name": db_name})
        )
        d = result.data
        if d["alive"]:
            return True, d["latency_ms"], None
        return False, None, d["error"] or "connection failed"

    @staticmethod
    def _driver_subtitle(factory) -> str:
        try:
            url = factory._engine.url
            driver = url.drivername.split("+")[0]
            host = url.host or "local"
            db = url.database or ""
            return f"{driver} · {host}/{db}" if db else f"{driver} · {host}"
        except Exception:
            return "—"

    # ── Card builder ───────────────────────────────────────────────────────
    def _make_cards(self, names: list[str]) -> tuple[list[ft.Control], int]:
        cards, alive = [], 0
        cache = type(self)._status_cache
        for name in names:
            r = cache.get(name)
            if r is None:
                state, status = "unknown", "connecting..."
            elif r[0]:
                alive += 1
                state, status = "alive", f"🟢 {r[1]:.1f} ms"
            else:
                state, status = "down", f"🔴 {r[2] or 'down'}"
            cards.append(StatusCard(
                state=state, icon=ft.Icons.STORAGE, name=name,
                subtitle=self._driver_subtitle(ConnectionRegistry.get(name)),
                status=status,
            ))
        return cards, alive

    # ── Sections ───────────────────────────────────────────────────────────
    def _empty_state(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.STORAGE, size=42, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("No SQL databases registered", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Add connection URLs to the vault to wire them up:",
                            size=12, color=ft.Colors.BLUE_GREY_300),
                    ft.Text("POSTGRES_URL          → default app database",
                            size=11, color=ft.Colors.BLUE_GREY_300, italic=True),
                    ft.Text("DATABASE_<NAME>       → named database (e.g. DATABASE_ANALYTICS)",
                            size=11, color=ft.Colors.BLUE_GREY_300, italic=True),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
            bgcolor=ft.Colors.BLUE_GREY_900,
            border_radius=12,
            alignment=ft.Alignment(0, 0),
        )

    def _header(self, count: int, alive_count: int) -> ft.Control:
        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("SQL Databases", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"{alive_count} of {count} live",
                            size=12, color=ft.Colors.BLUE_GREY_300,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Icon(ft.Icons.STORAGE, size=28, color=ft.Colors.BLUE_400),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def build_content(self):
        names = sorted(ConnectionRegistry.list())
        tabs = AdminTabs(self.page.route or "/admin/databases", self.nav_service)

        if not names:
            return ft.Column([tabs, self._empty_state()], spacing=0)

        body = ft.Column(spacing=10)

        def _fill_body():
            cards, alive = self._make_cards(names)
            body.controls = [
                self._header(len(names), alive),
                ft.Container(height=8),
                *cards,
                ft.Row(
                    [ft.TextButton(
                        content=ft.Text("↺  Refresh connections"),
                        on_click=lambda _: _on_refresh(),
                    )],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ]

        async def _run_probe():
            uncached = [n for n in names if n not in type(self)._status_cache]
            if not uncached:
                return
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as ex:
                results = await loop.run_in_executor(
                    None, lambda: list(ex.map(self._probe, uncached))
                )
            type(self)._status_cache.update(dict(zip(uncached, results)))
            _fill_body()
            self.page.update()

        def _on_refresh():
            type(self)._status_cache.clear()
            _fill_body()
            self.page.update()
            self.page.run_task(_run_probe)

        _fill_body()
        self.page.run_task(_run_probe)

        return ft.Column([tabs, body], spacing=0)


def view(page: ft.Page, props: dict) -> ft.View:
    """Router entry point."""
    return AdminDatabasesView(page, props).render()
