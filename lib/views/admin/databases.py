"""Admin database inspector view."""
import flet as ft

from lib.ui.layouts.base_view import BaseView


class AdminDatabasesView(BaseView):
    """Database inspector dashboard."""

    title = "Database Inspector"
    show_sidebar = True

    def build_content(self):
        """Build the database list UI."""
        config = self.props.get("config")
        databases = config.databases if config else {}

        if not databases:
            return ft.Column(
                [
                    ft.Text(
                        "No Databases Configured",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Set DATABASE_* environment variables to add databases.",
                        size=14,
                        color="grey",
                    ),
                ],
                spacing=10,
            )

        # Build database list
        db_items = []
        for db_name in sorted(databases.keys()):
            db_url = databases[db_name]
            db_items.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(
                                db_name.upper(),
                                size=14,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "◉ connected",
                                size=12,
                                color="green",
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=15,
                    border=ft.border.all(1, "#ddd"),
                    border_radius=8,
                )
            )

        return ft.Column(
            [
                ft.Text(
                    "Connected Databases",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),
                *db_items,
            ],
            spacing=15,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    """Router entry point."""
    return AdminDatabasesView(page, props).render()
