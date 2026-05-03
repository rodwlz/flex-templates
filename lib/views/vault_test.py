"""Test view — retrieve and display POSTGRES_USER from vault."""
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest


class VaultTestView(BaseView):
    title = "Vault Test"
    show_sidebar = True

    def build_content(self):
        """Pull POSTGRES_USER from vault and display it."""
        # Get the secret
        result = self._vault_service.execute(
            ActionRequest(action="get", data={"key": "POSTGRES_USER"})
        )

        if result.success:
            user_value = result.data["value"]
            display = ft.Column([
                ft.Text("✓ Secret Retrieved", size=16, weight="bold", color=ft.Colors.GREEN),
                ft.Divider(),
                ft.Text("Key: POSTGRES_USER", size=12, weight="bold"),
                ft.Text(f"Value: {user_value}", size=12, color=ft.Colors.BLUE_ACCENT_700),
            ])
        else:
            error = result.error
            display = ft.Column([
                ft.Text("✗ Error Retrieving Secret", size=16, weight="bold", color=ft.Colors.RED),
                ft.Divider(),
                ft.Text(f"Error: {error}", size=12, color=ft.Colors.RED),
                ft.Text(
                    "Common causes:\n"
                    "• Vault is locked (go to /security and unlock)\n"
                    "• Secret not found (add it via /security password manager)\n"
                    "• Vault not initialized (go to /security first time)",
                    size=11,
                    color="gray",
                ),
            ])

        return ft.Column([
            ft.Text("Vault Test", size=18, weight="bold"),
            ft.Text("Retrieving POSTGRES_USER secret from vault...", size=12, color="gray"),
            ft.Divider(),
            display,
        ])


def view(page, props):
    """Entry point for router."""
    return VaultTestView(page, props).render()
