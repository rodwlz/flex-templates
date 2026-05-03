"""StatusCard component: shared live-status row for admin views."""
import flet as ft

from lib.ui.components.status_card import StatusCard


def test_renders_with_alive_state():
    card = StatusCard(
        state="alive",
        icon=ft.Icons.STORAGE,
        name="northwind",
        subtitle="postgresql · 192.168.0.108",
        status="🟢 12.3 ms",
    )
    assert isinstance(card, ft.Container)


def test_renders_with_down_state():
    card = StatusCard(
        state="down",
        icon=ft.Icons.BOLT,
        name="redis",
        subtitle=None,
        status="🔴 connection refused",
    )
    assert isinstance(card, ft.Container)


def test_card_includes_name_and_status_in_controls():
    card = StatusCard(
        state="alive",
        icon=ft.Icons.STORAGE,
        name="analytics",
        subtitle="warehouse",
        status="🟢 5.2 ms",
    )
    rendered = str(card.content.controls)
    assert "ANALYTICS" in rendered
    assert "5.2 ms" in rendered
    assert "warehouse" in rendered


def test_card_without_subtitle_renders():
    """Subtitle is optional — card should still render cleanly when omitted."""
    card = StatusCard(
        state="unknown",
        icon=ft.Icons.STORAGE,
        name="loading",
        subtitle=None,
        status="…",
    )
    assert isinstance(card, ft.Container)
