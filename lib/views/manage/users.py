"""Manage Users view — paginated list with create and delete."""
from __future__ import annotations

import flet as ft

from lib.ui.components.manage_tabs import ManageTabs
from lib.ui.layouts.protected_view import ProtectedView


class ManageUsersView(ProtectedView):
    title = "Manage Users"
    show_sidebar = True

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._cur_page = 1
        self._search_query = ""
        self._body: ft.Column | None = None
        # Add-user form fields (assigned in build_content)
        self._new_username: ft.TextField | None = None
        self._new_email: ft.TextField | None = None
        self._new_password: ft.TextField | None = None
        self._form_error: ft.Text | None = None
        self._show_form: bool = False

    # ── Data loading ──────────────────────────────────────────────────────

    def _load_page(self, page_num: int = 1):
        self._cur_page = page_num
        return self._backend.list_users(page=page_num, page_size=15)

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_search(self, e):
        self._search_query = e.control.value.strip()
        self._refresh_body()

    def _on_prev(self, _e):
        if self._cur_page > 1:
            self._refresh_body(self._cur_page - 1)

    def _on_next(self, _e, total_pages: int):
        if self._cur_page < total_pages:
            self._refresh_body(self._cur_page + 1)

    def _on_delete(self, user_id: str, username: str):
        self._backend.delete_user(user_id)
        self._refresh_body()
        self._snack(f"Deleted {username}")

    def _on_toggle_form(self, _e):
        self._show_form = not self._show_form
        self._refresh_body()

    def _on_add_user(self, _e):
        username = self._new_username.value.strip()
        email = self._new_email.value.strip()
        password = self._new_password.value.strip()

        if not username or not email or not password:
            self._form_error.value = "All fields are required."
            self.page.update()
            return

        try:
            self._backend.create_user({"username": username, "email": email, "password": password})
            self._show_form = False
            self._refresh_body()
            self._snack(f"Created {username}")
        except Exception as exc:
            self._form_error.value = str(exc)
            self.page.update()

    # ── UI builders ───────────────────────────────────────────────────────

    def _build_table(self, result: dict) -> ft.Control:
        rows = []
        for user in result["items"]:
            roles_text = ", ".join(user.get("roles", [])) if user.get("roles") else "—"
            rows.append(ft.DataRow([
                ft.DataCell(ft.Text(user["username"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(user.get("email", ""), size=12)),
                ft.DataCell(ft.Text(roles_text, size=12, color=ft.Colors.BLUE_GREY_300)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        icon_color=ft.Colors.RED_300,
                        tooltip=f"Delete {user['username']}",
                        on_click=lambda _e, uid=user["id"], uname=user["username"]:
                            self._on_delete(uid, uname),
                    )
                ),
            ]))

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Username")),
                ft.DataColumn(ft.Text("Email")),
                ft.DataColumn(ft.Text("Roles")),
                ft.DataColumn(ft.Text("")),
            ],
            rows=rows,
        )

        total_pages = result["pages"]
        page_label = ft.Text(f"Page {result['page']} of {total_pages}  ({result['total']} total)",
                             size=12, color=ft.Colors.BLUE_GREY_300)

        pagination = ft.Row([
            ft.TextButton(
                content=ft.Text("← Prev"),
                disabled=result["page"] <= 1,
                on_click=self._on_prev,
            ),
            page_label,
            ft.TextButton(
                content=ft.Text("Next →"),
                disabled=result["page"] >= total_pages,
                on_click=lambda e, tp=total_pages: self._on_next(e, tp),
            ),
        ], spacing=8)

        return ft.Column([table, pagination], spacing=8)

    def _build_add_form(self) -> ft.Control:
        self._new_username = ft.TextField(label="Username", width=200)
        self._new_email = ft.TextField(label="Email", width=220)
        self._new_password = ft.TextField(label="Password", password=True, width=180)
        self._form_error = ft.Text("", color=ft.Colors.RED_400, size=12)

        return ft.Container(
            content=ft.Column([
                ft.Text("New User", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([self._new_username, self._new_email, self._new_password], spacing=10),
                ft.Row([
                    ft.ElevatedButton(content=ft.Text("Create"), on_click=self._on_add_user),
                    ft.TextButton(content=ft.Text("Cancel"), on_click=self._on_toggle_form),
                ], spacing=8),
                self._form_error,
            ], spacing=8),
            bgcolor=ft.Colors.BLUE_GREY_900,
            border_radius=8,
            padding=16,
        )

    def _refresh_body(self, page_num: int | None = None):
        if self._body is None:
            return
        page_num = page_num or self._cur_page
        result = self._load_page(page_num)
        controls = [self._build_table(result)]
        if self._show_form:
            controls.append(self._build_add_form())
        self._body.controls = controls
        self._body.update()

    def _snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), duration=1500)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def build_content(self):
        tabs = ManageTabs(self.page.route or "/manage/users", self.nav_service)

        search = ft.TextField(
            label="Search by username",
            width=280,
            on_change=self._on_search,
            prefix_icon=ft.Icons.SEARCH,
        )
        add_btn = ft.ElevatedButton(
            content=ft.Text("+ Add User"),
            on_click=self._on_toggle_form,
        )
        toolbar = ft.Row([search, add_btn], spacing=12)

        result = self._load_page(1)
        self._body = ft.Column([self._build_table(result)], spacing=8)

        return ft.Column([tabs, toolbar, self._body], spacing=16)


def view(page: ft.Page, props: dict) -> ft.View:
    return ManageUsersView(page, props).render()
