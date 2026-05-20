"""Manage Roles view — list, create, delete."""
from __future__ import annotations

import flet as ft

from lib.ui.components.manage_tabs import ManageTabs
from lib.ui.layouts.protected_view import ProtectedView


class ManageRolesView(ProtectedView):
    title = "Manage Roles"
    show_sidebar = True

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._body: ft.Column | None = None
        self._role_name_field: ft.TextField | None = None
        self._error_text: ft.Text | None = None

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_create_role(self, _e):
        name = self._role_name_field.value.strip()
        if not name:
            self._error_text.value = "Role name is required."
            self.page.update()
            return

        try:
            self._backend.create_role(name)
            self._role_name_field.value = ""
            self._error_text.value = ""
            self._refresh_body()
            self._snack(f"Role '{name}' created")
        except Exception as exc:
            self._error_text.value = str(exc)
            self.page.update()

    def _on_delete_role(self, role_id: str, name: str):
        self._backend.delete_role(role_id)
        self._refresh_body()
        self._snack(f"Role '{name}' deleted")

    # ── UI builders ───────────────────────────────────────────────────────

    def _build_table(self, roles: list[dict]) -> ft.Control:
        if not roles:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.VERIFIED_USER, size=36, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("No roles defined yet.", size=14, color=ft.Colors.BLUE_GREY_300),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=30,
                bgcolor=ft.Colors.BLUE_GREY_900,
                border_radius=8,
                alignment=ft.Alignment(0, 0),
            )

        rows = [
            ft.DataRow([
                ft.DataCell(ft.Text(r["name"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(r.get("description") or "—", size=12,
                                    color=ft.Colors.BLUE_GREY_300)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        icon_color=ft.Colors.RED_300,
                        tooltip=f"Delete {r['name']}",
                        on_click=lambda _e, rid=r["id"], rname=r["name"]:
                            self._on_delete_role(rid, rname),
                    )
                ),
            ])
            for r in roles
        ]

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Description")),
                ft.DataColumn(ft.Text("")),
            ],
            rows=rows,
        )

    def _refresh_body(self):
        if self._body is None:
            return
        roles = self._backend.list_roles()
        self._body.controls = [self._build_table(roles)]
        self._body.update()

    def _snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), duration=1500)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def build_content(self):
        tabs = ManageTabs(self.page.route or "/manage/roles", self.nav_service)

        self._role_name_field = ft.TextField(label="Role name", width=240, autofocus=False)
        self._error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

        create_row = ft.Row([
            self._role_name_field,
            ft.ElevatedButton(content=ft.Text("+ Create"), on_click=self._on_create_role),
            self._error_text,
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        roles = self._backend.list_roles()
        self._body = ft.Column([self._build_table(roles)], spacing=8)

        return ft.Column([tabs, create_row, ft.Divider(height=16), self._body], spacing=8)


def view(page: ft.Page, props: dict) -> ft.View:
    return ManageRolesView(page, props).render()
