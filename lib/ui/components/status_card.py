"""StatusCard — consistent live-status row used by admin inspector views.

Layout:
    [icon] [name + subtitle] ...spacer... [status pill]

The card border tints green/red/grey based on state so a long list of
services scans easily. Used by AdminDatabasesView and AdminCachesView.
"""
from __future__ import annotations

import flet as ft


_STATE_COLORS = {
    "alive":   (ft.Colors.GREEN_400,  ft.Colors.GREEN_900),
    "down":    (ft.Colors.RED_400,    ft.Colors.RED_900),
    "unknown": (ft.Colors.GREY_500,   ft.Colors.GREY_900),
}


class StatusCard(ft.Container):
    """A single service entry with icon, label, subtitle, and a status pill.

    state:    "alive" | "down" | "unknown"
    icon:     ft.Icons.* enum value
    name:     primary label (e.g. "northwind", "redis_main")
    subtitle: secondary line (e.g. driver, host, key count) — optional
    status:   status pill text (e.g. "🟢 12.3 ms · 4 keys")
    """

    def __init__(
        self,
        *,
        state: str,
        icon,
        name: str,
        subtitle: str | None,
        status: str,
    ):
        accent, dark = _STATE_COLORS.get(state, _STATE_COLORS["unknown"])

        left = ft.Container(
            content=ft.Icon(icon, size=22, color=accent),
            width=44, height=44,
            bgcolor=dark, border_radius=10,
            alignment=ft.Alignment(0, 0),  # center
        )

        text_col = [ft.Text(name.upper(), size=14, weight=ft.FontWeight.BOLD)]
        if subtitle:
            text_col.append(ft.Text(subtitle, size=11, color=ft.Colors.BLUE_GREY_300))

        body = ft.Column(text_col, spacing=2, expand=True)

        pill = ft.Container(
            content=ft.Text(status, size=11, weight=ft.FontWeight.W_500, color=accent),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor=dark, border_radius=12,
        )

        super().__init__(
            content=ft.Row([left, body, pill], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.BLUE_GREY_900,
            border=ft.border.all(1, ft.Colors.with_opacity(0.4, accent)),
            border_radius=12,
        )
