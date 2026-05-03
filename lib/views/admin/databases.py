"""Admin database inspector view — live status for every registered SQL database."""
from __future__ import annotations

from urllib.parse import urlparse

import flet as ft

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.connection_tester import ConnectionTester
from lib.ui.components.admin_tabs import AdminTabs
from lib.ui.components.status_card import StatusCard
from lib.ui.layouts.base_view import BaseView


class AdminDatabasesView(BaseView):
    """Database inspector dashboard — pings each registered SQL connection."""

    title = "Database Inspector"
    show_sidebar = True

    # ── Connection probing ─────────────────────────────────────────────────
    def _probe(self, db_name: str) -> tuple[bool, float | None, str | None]:
        try:
            factory = ConnectionRegistry.get(db_name)
            result = ConnectionTester(factory).execute(
                ActionRequest(action="test", data={})
            )
            if result.success and result.data.get("alive"):
                return True, result.data.get("latency_ms"), None
            return False, None, result.error or "connection failed"
        except RuntimeError:
            return False, None, "not registered"
        except Exception as exc:
            return False, None, str(exc)

    @staticmethod
    def _driver_subtitle(factory) -> str:
        """Render 'driver · host' for the card subtitle."""
        try:
            url = factory._engine.url
            driver = url.drivername.split("+")[0]
            host = url.host or "local"
            db = url.database or ""
            return f"{driver} · {host}/{db}" if db else f"{driver} · {host}"
        except Exception:
            return "—"

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
        databases = ConnectionRegistry._factories
        tabs = AdminTabs(self.page.route or "/admin/databases", self.nav_service)

        if not databases:
            return ft.Column([tabs, self._empty_state()], spacing=0)

        # Probe all and assemble cards.
        cards: list[ft.Control] = []
        alive_count = 0
        for name in sorted(databases):
            alive, latency_ms, error = self._probe(name)
            if alive:
                alive_count += 1
                status = f"🟢 {latency_ms:.1f} ms"
                state = "alive"
            else:
                status = f"🔴 {error or 'down'}"
                state = "down"

            cards.append(
                StatusCard(
                    state=state,
                    icon=ft.Icons.STORAGE,
                    name=name,
                    subtitle=self._driver_subtitle(databases[name]),
                    status=status,
                )
            )

        return ft.Column(
            [
                tabs,
                self._header(len(databases), alive_count),
                ft.Container(height=8),  # spacer
                *cards,
            ],
            spacing=10,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    """Router entry point."""
    return AdminDatabasesView(page, props).render()
