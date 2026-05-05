"""Admin cache inspector view — live status for every registered cache adapter."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import flet as ft

from lib.contracts.base import ActionRequest
from lib.services.cache_registry import CacheRegistry
from lib.ui.components.admin_tabs import AdminTabs
from lib.ui.components.status_card import StatusCard
from lib.ui.layouts.base_view import BaseView


class AdminCachesView(BaseView):
    """Cache inspector dashboard — pings each registered cache adapter."""

    title = "Cache Inspector"
    show_sidebar = True

    # Persists across navigation — cleared only by the Refresh button.
    _status_cache: dict[str, dict] = {}

    # ── Probing ────────────────────────────────────────────────────────────
    def _probe(self, name: str) -> dict:
        result = self.props["cache_tester"].execute(
            ActionRequest(action="test", data={"name": name})
        )
        return result.data

    @staticmethod
    def _adapter_subtitle(name: str, adapter) -> str:
        client = getattr(adapter, "_r", None)
        kind = type(adapter).__name__.replace("Adapter", "").lower()
        try:
            kwargs = client.connection_pool.connection_kwargs
            host = kwargs.get("host", "?")
            port = kwargs.get("port", "?")
            return f"{kind} · {host}:{port}"
        except Exception:
            return kind

    # ── Card builder ───────────────────────────────────────────────────────
    def _make_cards(self, names: list[str]) -> tuple[list[ft.Control], int]:
        cards, alive = [], 0
        cache = type(self)._status_cache
        for name in names:
            adapter = CacheRegistry.get(name)
            r = cache.get(name)
            if r is None:
                state, status = "unknown", "connecting..."
            elif r["alive"]:
                alive += 1
                state = "alive"
                status = f"🟢 {r['latency_ms']:.1f} ms · {r['info']}"
            else:
                state = "down"
                status = f"🔴 {r['error'] or 'down'}"
            cards.append(StatusCard(
                state=state, icon=ft.Icons.BOLT, name=name,
                subtitle=self._adapter_subtitle(name, adapter), status=status,
            ))
        return cards, alive

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

        sorted_names = sorted(names)
        body = ft.Column(spacing=10)

        def _fill_body():
            cards, alive = self._make_cards(sorted_names)
            body.controls = [
                self._header(len(sorted_names), alive),
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
            uncached = [n for n in sorted_names if n not in type(self)._status_cache]
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
    return AdminCachesView(page, props).render()
