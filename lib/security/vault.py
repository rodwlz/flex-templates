"""Thin wrapper around VaultService with a clean dict-like API.

Usage in views / services:
    vault = props["vault"]
    user = vault.get("POSTGRES_USER")

Usage in standalone scripts:
    from lib.security.vault import open_vault
    vault = open_vault()
    print(vault.get("POSTGRES_USER"))
"""
import os
from lib.contracts.base import ActionRequest
from lib.security.vault_service import VaultService
from lib.security.vault_store import VaultStore


class Vault:
    """Simple interface over VaultService. No ActionRequest boilerplate needed."""

    def __init__(self, service: VaultService):
        self._service = service

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return the secret value for *key*.

        Returns *default* if the key doesn't exist in the vault.
        Raises RuntimeError if the vault is locked or another error occurs.
        """
        result = self._service.execute(ActionRequest(action="get", data={"key": key}))
        if result.success:
            return result.data["value"]
        if "not found" in (result.error or "").lower():
            return default
        raise RuntimeError(f"Vault error for '{key}': {result.error}")

    def set(self, key: str, value: str) -> None:
        """Write *key* = *value* into the vault (in memory only until save())."""
        result = self._service.execute(
            ActionRequest(action="set", data={"key": key, "value": value})
        )
        if not result.success:
            raise RuntimeError(f"Failed to set '{key}': {result.error}")

    def delete(self, key: str) -> None:
        """Remove *key* from the vault (in memory only until save())."""
        result = self._service.execute(
            ActionRequest(action="delete", data={"key": key})
        )
        if not result.success:
            raise RuntimeError(f"Failed to delete '{key}': {result.error}")

    def keys(self) -> list[str]:
        """Return all stored key names (never values)."""
        result = self._service.execute(ActionRequest(action="list_keys"))
        return result.data.get("keys", []) if result.success else []

    def save(self) -> None:
        """Persist all in-memory changes to disk."""
        result = self._service.execute(ActionRequest(action="save", data={}))
        if not result.success:
            raise RuntimeError(f"Failed to save vault: {result.error}")

    def unlock(self, key: str | None = None) -> bool:
        """Unlock vault. Uses .secrets/.env master key when *key* is omitted."""
        result = self._service.execute(
            ActionRequest(action="unlock", data={"key": key})
        )
        return result.success

    def lock(self) -> None:
        """Clear decrypted state from memory."""
        self._service.execute(ActionRequest(action="lock"))

    @property
    def is_locked(self) -> bool:
        result = self._service.execute(ActionRequest(action="status"))
        return not result.data.get("unlocked", True)


def open_vault(
    vault_path: str = ".secrets/vault.json",
    env_path: str = ".secrets/.env",
) -> Vault:
    """Open and auto-unlock the vault for use in standalone scripts.

    Reads master key from *env_path* automatically — no manual key entry.

    Example:
        vault = open_vault()
        print(vault.get("POSTGRES_USER"))
    """
    service = VaultService(
        store=VaultStore(path=vault_path),
        master_key=os.getenv("VAULT_MASTER_KEY", ""),
        confirm_key=os.getenv("VAULT_CONFIRM_KEY", ""),
        env_path=env_path,
    )
    vault = Vault(service)

    status = service.execute(ActionRequest(action="status"))
    if not status.data.get("ready"):
        raise RuntimeError(
            "Vault is not initialized. Run the app and go to /security first."
        )

    if not vault.unlock():
        raise RuntimeError(
            "Failed to unlock vault. Check VAULT_MASTER_KEY in .secrets/.env"
        )

    return vault
