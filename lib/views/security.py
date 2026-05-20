"""Security view — password manager for encrypted vault."""
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.ui.layouts.protected_view import ProtectedView
from lib.ui.components.copy_button import CopyButton
from lib.contracts.base import ActionRequest


class SecurityView(ProtectedView):
    title = "Security & Secrets"
    show_sidebar = True

    def __init__(self, page, props):
        super().__init__(page, props)
        self._vault_service = props["vault_service"]
        self._current_state = "init"  # init, show_keys, locked, unlocked, error
        self._keys = {}  # cached keys list
        self._reveal_key = None  # which key to reveal
        self._content_container: ft.Container | None = None  # set in build_content
        self._new_master_key: str | None = None  # populated by bootstrap
        self._new_confirm_key: str | None = None
        self._bootstrap_error: str = ""  # bootstrap error (for error state)
        self._unlock_error: str = ""  # unlock form error
        self._unlocked_error: str = ""  # password manager error

    # ── State checks ───────────────────────────────────────────────────────

    def _refresh_status(self) -> dict:
        """Get current vault status."""
        result = self._vault_service.execute(ActionRequest(action="status"))
        return result.data if result.success else {}

    def _resolve_state(self):
        """Inspect the vault and set self._current_state accordingly.

        First launch: bootstrap the vault on disk (creates .secrets/.env and
        .secrets/vault.json), then show the generated keys to the user.
        """
        status = self._refresh_status()

        # Not ready (vault and/or env files missing) → bootstrap
        if not status.get("ready"):
            result = self._vault_service.execute(ActionRequest(action="bootstrap"))
            if not result.success:
                self._current_state = "error"
                self._bootstrap_error = result.error or "Failed to initialize vault"
                return
            self._new_master_key = result.data["master_key"]
            self._new_confirm_key = result.data["confirm_key"]
            self._current_state = "show_keys"
            return

        # Ready but not unlocked → show unlock form
        if not status.get("unlocked"):
            self._current_state = "locked"
            return

        # Ready and unlocked → show password manager
        self._current_state = "unlocked"
        self._load_keys()

    def _load_keys(self):
        """Fetch list of secret keys from vault."""
        result = self._vault_service.execute(ActionRequest(action="list_keys"))
        if result.success:
            self._keys = {key: None for key in result.data.get("keys", [])}

    # ── Unlock handlers ────────────────────────────────────────────────────

    def _unlock_vault(self, e):
        """Unlock vault with entered key."""
        key = self._unlock_field.value.strip()
        if not key:
            self._unlock_error = "Enter the master key"
            self._refresh_ui()
            return

        result = self._vault_service.execute(
            ActionRequest(action="unlock", data={"key": key})
        )

        if result.success:
            self._unlock_error = ""
            self._current_state = "unlocked"
            self._load_keys()
            self.events.emit("vault.unlocked", {})
            self._refresh_ui()
        else:
            self._unlock_error = result.error or "Failed to unlock vault"
            self._refresh_ui()

    def _continue_to_unlock(self, e):
        """User has saved the displayed keys — move on to the unlock screen."""
        self._new_master_key = None
        self._new_confirm_key = None
        self._current_state = "locked"
        self._refresh_ui()

    # ── Secret management ──────────────────────────────────────────────────

    def _reveal_secret(self, key, button):
        """Toggle reveal for a secret value."""
        if self._reveal_key == key:
            self._reveal_key = None
        else:
            self._reveal_key = key
        self._refresh_ui()

    def _on_delete_secret(self, key):
        """Delete a secret."""
        result = self._vault_service.execute(
            ActionRequest(action="delete", data={"key": key})
        )
        if result.success:
            self._keys.pop(key, None)
            self._show_snackbar(f"Secret '{key}' deleted")
            self._refresh_ui()
        else:
            self._unlocked_error = result.error
            self._refresh_ui()

    def _add_secret(self, e):
        """Add a new secret to the vault."""
        key = self._add_key_field.value.strip()
        value = self._add_value_field.value.strip()

        if not key:
            self._unlocked_error = "Key cannot be empty"
            self._refresh_ui()
            return
        if key in self._keys:
            self._unlocked_error = f"Key '{key}' already exists"
            self._refresh_ui()
            return

        result = self._vault_service.execute(
            ActionRequest(action="set", data={"key": key, "value": value})
        )
        if result.success:
            self._keys[key] = value
            self._add_key_field.value = ""
            self._add_value_field.value = ""
            self._unlocked_error = ""
            self._show_snackbar(f"Secret '{key}' added")
            self._load_keys()
            self._refresh_ui()
        else:
            self._unlocked_error = result.error or "Failed to add secret"
            self._refresh_ui()

    def _on_save_changes(self, e):
        """Save changes directly — user is already unlocked."""
        result = self._vault_service.execute(
            ActionRequest(action="save", data={})
        )

        if result.success:
            self._unlocked_error = ""
            self._show_snackbar("✓ Vault saved to disk")
        else:
            self._unlocked_error = result.error or "Failed to save"
            self._show_snackbar(f"❌ Save failed: {self._unlocked_error}", duration=3000)
        self.page.update()

    def _confirm_and_save(self, e):
        """Save with confirmation key (optional dialog for extra security)."""
        confirm_key = self._confirm_key_field.value.strip()

        result = self._vault_service.execute(
            ActionRequest(action="save", data={"confirm_key": confirm_key})
        )

        self._confirm_dialog.open = False
        self._confirm_key_field.value = ""
        self.page.dialog = None

        if result.success:
            self._unlocked_error = ""
            self._show_snackbar("✓ Changes saved securely")
        else:
            self._unlocked_error = result.error or "Failed to save"
        self._refresh_ui()

    # ── UI builders ────────────────────────────────────────────────────────

    def _retry_bootstrap(self, e):
        """Retry bootstrap after an error."""
        self._resolve_state()
        self._refresh_ui()

    def _build_error(self) -> ft.Control:
        """Error screen — bootstrap or initialization failed."""
        return ft.Column([
            ft.Text("Vault Error", size=18, weight="bold", color=ft.Colors.RED),
            ft.Text(self._bootstrap_error, size=12, color="gray"),
            ft.Divider(),
            ft.Text(
                "The vault couldn't be created. Check that .secrets/ directory "
                "is writable and try again.",
                size=11,
            ),
            ft.ElevatedButton("Retry", on_click=self._retry_bootstrap),
        ])

    def _build_show_keys(self) -> ft.Control:
        """Post-bootstrap screen: surface the generated keys for the user to save."""
        self._error_text = ft.Text("", color=ft.Colors.RED, size=12)

        return ft.Column([
            ft.Text("Vault Initialized", size=18, weight="bold"),
            ft.Text(
                "Save these keys somewhere safe — they're stored in .secrets/.env "
                "and you'll need the Master Key to unlock the vault.",
                size=12,
                color="gray",
            ),
            ft.Divider(),
            self._build_key_row("Master Key", self._new_master_key),
            self._build_key_row("Confirmation Key", self._new_confirm_key),
            ft.Text(
                "The Confirmation Key is only required when saving changes to disk.",
                size=11,
                color="orange",
            ),
            ft.ElevatedButton("I've saved them — Continue", on_click=self._continue_to_unlock),
            self._error_text,
        ])

    def _build_key_row(self, label: str, value: str) -> ft.Control:
        """Read-only key field with a working copy-to-clipboard button."""
        return ft.Row([
            ft.Column([
                ft.Text(label, weight="bold", size=11),
                ft.TextField(
                    value=value,
                    read_only=True,
                    text_size=10,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                    border_radius=5,
                ),
            ], expand=True),
            CopyButton(self.page, value),
        ])

    def _build_locked(self) -> ft.Control:
        """Locked state: show key entry form."""
        self._unlock_field = ft.TextField(
            label="Master Key", password=True, autofocus=True
        )

        return ft.Column([
            ft.Text("Unlock Vault", size=18, weight="bold"),
            ft.Text("Enter your master key to access secrets.", size=12, color="gray"),
            ft.Divider(),
            self._unlock_field,
            ft.Text(self._unlock_error, color=ft.Colors.RED, size=12),
            ft.ElevatedButton("Unlock", on_click=self._unlock_vault),
        ])

    def _build_unlocked(self) -> ft.Control:
        """Unlocked state: password manager."""

        rows = []
        for key in self._keys:
            result = self._vault_service.execute(
                ActionRequest(action="get", data={"key": key})
            )
            value = result.data.get("value", "") if result.success else ""
            revealed = self._reveal_key == key

            rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Text(key, weight="bold")),
                    ft.DataCell(ft.Text("•••••" if not revealed else value, size=11)),
                    ft.DataCell(
                        ft.Row([
                            ft.IconButton(
                                ft.Icons.VISIBILITY if not revealed else ft.Icons.VISIBILITY_OFF,
                                icon_size=18,
                                on_click=lambda e, k=key, row=None: self._reveal_secret(k, row),
                                tooltip="Toggle",
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_size=18,
                                on_click=lambda e, k=key: self._on_delete_secret(k),
                                tooltip="Delete",
                            ),
                        ], spacing=0),
                    ),
                ])
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Key")),
                ft.DataColumn(ft.Text("Value")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=rows,
            width=1000,
        )

        # Add Secret form
        self._add_key_field = ft.TextField(label="Key", width=200)
        self._add_value_field = ft.TextField(label="Value", width=300)

        # Build confirmation dialog
        self._confirm_key_field = ft.TextField(label="Confirmation Key", password=True)
        self._confirm_error = ft.Text("", color=ft.Colors.RED, size=11)
        self._confirm_dialog = ft.AlertDialog(
            title=ft.Text("Confirm Changes"),
            content=ft.Column([
                ft.Text("Enter your confirmation key to save changes to disk:"),
                self._confirm_key_field,
                self._confirm_error,
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self._confirm_dialog, "open", False)),
                ft.TextButton("Save", on_click=self._confirm_and_save),
            ],
        )

        return ft.Column([
            ft.Text("Secrets Manager", size=18, weight="bold"),
            ft.Text(self._unlocked_error, color=ft.Colors.RED, size=12),
            ft.Divider(),
            ft.Row([
                ft.Text(f"{len(self._keys)} secret(s)", size=12, color="gray"),
                ft.IconButton(
                    ft.Icons.REFRESH,
                    on_click=lambda e: (self._load_keys(), self._refresh_ui()),
                    tooltip="Refresh",
                ),
            ]),
            ft.Container(content=table, expand=True),
            ft.Divider(),
            ft.Text("Add Secret", size=13, weight="bold"),
            ft.Row([
                self._add_key_field,
                self._add_value_field,
                ft.ElevatedButton("Add", on_click=self._add_secret),
            ]),
            ft.Row([
                ft.ElevatedButton(
                    "Save Changes",
                    on_click=self._on_save_changes,
                ),
                ft.TextButton("Lock", on_click=lambda e: self._lock_vault()),
            ]),
        ])

    # ── Helpers ────────────────────────────────────────────────────────────

    def _lock_vault(self):
        """Lock vault."""
        self._vault_service.execute(ActionRequest(action="lock"))
        self._current_state = "locked"
        self._keys.clear()
        self._refresh_ui()

    def _show_snackbar(self, message: str, duration: int = 1500):
        """Show a brief notification toast."""
        snack = ft.SnackBar(content=ft.Text(message), duration=duration)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def _build_current_state(self) -> ft.Control:
        match self._current_state:
            case "show_keys":
                return self._build_show_keys()
            case "locked":
                return self._build_locked()
            case "unlocked":
                return self._build_unlocked()
            case "error":
                return self._build_error()
            case _:
                return ft.Text("Loading...")

    def _refresh_ui(self):
        """Swap the dynamic container's content based on current state."""
        if self._content_container is None:
            return  # not yet mounted; build_content will pick up the new state
        self._content_container.content = self._build_current_state()
        self._content_container.update()

    def build_content(self) -> ft.Control:
        """Entry point — resolve state up-front and return the dynamic container."""
        self._resolve_state()
        self._content_container = ft.Container(
            content=self._build_current_state(),
            expand=True,
        )
        return self._content_container


def view(page, props):
    return SecurityView(page, props).render()
