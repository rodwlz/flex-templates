"""Admin cache inspector view — live status for every registered cache adapter."""
from __future__ import annotations

import flet as ft

from lib.services.cache_registry import CacheRegistry
from lib.services.cache_tester import CacheTester
from lib.ui.components.admin_tabs import AdminTabs
from lib.ui.components.status_card import StatusCard
from lib.ui.layouts.base_view import BaseView


class AdminCachesView(BaseView):
    """Cache inspector dashboard — pings each registered cache adapter."""

    title = "Cache Inspector"
    show_sidebar = True

    # ── Probing ────────────────────────────────────────────────────────────
    def _probe(self, name: str) -> dict:
        try:
            adapter = CacheRegistry.get(name)
            return CacheTester(adapter).test({})
        except Exception as exc:
            return {"alive": False, "latency_ms": None, "info": None, "error": str(exc)}

    @staticmethod
    def _adapter_subtitle(name: str, adapter) -> str:
        """Best-effort 'service · host' subtitle from the adapter's underlying client."""
        # Adapters keep their client at conventional attrs; fall back gracefully.
        client = getattr(adapter, "_r", None)
        kind = type(adapter).__name__.replace("Adapter", "").lower()
        try:
            kwargs = client.connection_pool.connection_kwargs
            host = kwargs.get("host", "?")
            port = kwargs.get("port", "?")
            return f"{kind} · {host}:{port}"
        except Exception:
            return kind

    # ── Sections ───────────────────────────────────────────────────────────
    def _empty_state(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.BOLT, size=42, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("No cache services registered", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Add a service URL to the vault to wire it up:",
                            size=12, color=ft.Colors.BLUE_GREY_300),
                    ft.Text("REDIS_URL              → default Redis instance",
                            size=11, color=ft.Colors.BLUE_GREY_300, italic=True),
                    ft.Text("REDIS_URL_<ID>         → named Redis (e.g. REDIS_URL_SESSIONS)",
                            size=11, color=ft.Colors.BLUE_GREY_300, italic=True),
                    ft.Text("REDIS_PASSWORD[_<ID>]  → matching password key",
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
                        ft.Text("Cache Services", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"{alive_count} of {count} live",
                            size=12, color=ft.Colors.BLUE_GREY_300,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Icon(ft.Icons.BOLT, size=28, color=ft.Colors.AMBER_400),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def build_content(self):
        names = CacheRegistry.list()
        tabs = AdminTabs(self.page.route or "/admin/caches", self.nav_service)

        if not names:
            return ft.Column([tabs, self._empty_state()], spacing=0)

        cards: list[ft.Control] = []
        alive_count = 0
        for name in sorted(names):
            adapter = CacheRegistry.get(name)
            r = self._probe(name)
            if r["alive"]:
                alive_count += 1
                status = f"🟢 {r['latency_ms']:.1f} ms · {r['info']}"
                state = "alive"
            else:
                status = f"🔴 {r['error'] or 'down'}"
                state = "down"

            cards.append(
                StatusCard(
                    state=state,
                    icon=ft.Icons.BOLT,
                    name=name,
                    subtitle=self._adapter_subtitle(name, adapter),
                    status=status,
                )
            )

        return ft.Column(
            [
                tabs,
                self._header(len(names), alive_count),
                ft.Container(height=8),
                *cards,
            ],
            spacing=10,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    """Router entry point."""
    return AdminCachesView(page, props).render()
