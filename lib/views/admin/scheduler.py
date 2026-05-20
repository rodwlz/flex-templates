"""Scheduler admin view — read-only inspector for registered APScheduler jobs."""
from __future__ import annotations

import flet as ft

from lib.ui.components.admin_tabs import AdminTabs
from lib.ui.layouts.protected_view import ProtectedView


class AdminSchedulerView(ProtectedView):
    title = "Scheduler"
    show_sidebar = True

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._body: ft.Column | None = None

    # ── UI builders ───────────────────────────────────────────────────────

    def _build_table(self, jobs: list[dict]) -> ft.Control:
        if not jobs:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SCHEDULE, size=42, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("No jobs scheduled", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Add jobs in main.py via scheduler.add_job(fn, trigger, ...)",
                        size=12, color=ft.Colors.BLUE_GREY_300,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40,
                bgcolor=ft.Colors.BLUE_GREY_900,
                border_radius=12,
                alignment=ft.alignment.center,
            )

        rows = [
            ft.DataRow([
                ft.DataCell(ft.Text(j["id"], size=12, color=ft.Colors.BLUE_GREY_300)),
                ft.DataCell(ft.Text(j["func_name"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(j["trigger"], size=12)),
                ft.DataCell(ft.Text(str(j["next_run_time"]) if j["next_run_time"] else "—", size=12)),
            ])
            for j in jobs
        ]

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Job ID")),
                ft.DataColumn(ft.Text("Function")),
                ft.DataColumn(ft.Text("Trigger")),
                ft.DataColumn(ft.Text("Next Run")),
            ],
            rows=rows,
        )

    def _refresh_body(self):
        if self._body is None:
            return
        jobs = self._backend.list_jobs()
        self._body.controls = [self._build_table(jobs)]
        self._body.update()
        self.page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def build_content(self):
        tabs = AdminTabs(self.page.route or "/admin/scheduler", self.nav_service)

        header = ft.Row([
            ft.Column([
                ft.Text("Scheduled Jobs", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Read-only — add/remove jobs in main.py",
                        size=12, color=ft.Colors.BLUE_GREY_300),
            ], spacing=2, expand=True),
            ft.TextButton(
                content=ft.Text("↺  Refresh"),
                on_click=lambda _: self._refresh_body(),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        jobs = self._backend.list_jobs()
        self._body = ft.Column([self._build_table(jobs)], spacing=8)

        return ft.Column([tabs, header, ft.Container(height=8), self._body], spacing=0)


def view(page: ft.Page, props: dict) -> ft.View:
    return AdminSchedulerView(page, props).render()
