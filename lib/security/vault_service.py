"""Vault service — manage encrypted secrets."""
import os
from pathlib import Path

from lib.contracts.base import ActionRequest, ActionResult
from lib.core.interfaces import IService
from lib.security.crypto import encrypt, decrypt, generate_key
from lib.security.vault_store import VaultStore


class VaultService(IService):
    """
    Encrypts/decrypts secrets on disk. Two-key design:
    - master_key: unlocks the vault (required to read/write)
    - confirm_key: required to persist changes to disk

    If `env_path` is given, the service loads master/confirm keys from that file
    (KEY=VALUE lines) at construction time and writes them there on bootstrap.
    """

    def __init__(
        self,
        store: VaultStore,
        master_key: str = "",
        confirm_key: str = "",
        env_path: str | None = None,
    ):
        self._store = store
        self._env_path = env_path
        self._master_key = master_key
        self._confirm_key = confirm_key
        self._secrets: dict | None = None  # None = locked

        # If an env file is configured and exists, load keys from it (file wins
        # over empty constructor args, but explicit args still take priority).
        if env_path and os.path.isfile(env_path):
            file_master, file_confirm = self._read_env_file(env_path)
            self._master_key = self._master_key or file_master
            self._confirm_key = self._confirm_key or file_confirm

    # ── Public contract interface ──────────────────────────────────────────

    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "unlock":
                return self._unlock(request.data.get("key", ""))
            case "get":
                return self._get(request.data.get("key"))
            case "list_keys":
                return self._list_keys()
            case "set":
                return self._set(request.data.get("key"), request.data.get("value"))
            case "delete":
                return self._delete(request.data.get("key"))
            case "save":
                return self._save(request.data.get("confirm_key", ""))
            case "lock":
                return self._lock()
            case "status":
                return self._status()
            case "bootstrap":
                return self._bootstrap()
            case _:
                return ActionResult(success=False, error=f"Unknown action: {request.action}")

    # ── Read-only properties ───────────────────────────────────────────────

    @property
    def unlocked(self) -> bool:
        return self._secrets is not None

    @property
    def vault_exists(self) -> bool:
        return self._store.exists()

    @property
    def env_exists(self) -> bool:
        return bool(self._env_path) and os.path.isfile(self._env_path)

    # ── Private actions ────────────────────────────────────────────────────

    def _unlock(self, key: str) -> ActionResult:
        if not key:
            key = self._master_key
            if not key:
                return ActionResult(
                    success=False, error="No master key provided (not in .env or argument)"
                )

        if key != self._master_key:
            return ActionResult(success=False, error="Invalid master key")

        if not self._store.exists():
            self._secrets = {}
            try:
                blob = encrypt({}, self._master_key)
                self._store.save(blob)
            except RuntimeError as e:
                return ActionResult(success=False, error=str(e))
            return ActionResult(success=True, data={"unlocked": True, "is_first_run": True})

        try:
            blob = self._store.load()
            self._secrets = decrypt(blob, self._master_key)
            return ActionResult(success=True, data={"unlocked": True, "is_first_run": False})
        except RuntimeError as e:
            return ActionResult(success=False, error=str(e))

    def _get(self, key: str) -> ActionResult:
        if not self.unlocked:
            return ActionResult(success=False, error="Vault is locked")
        if not key:
            return ActionResult(success=False, error="Key is required")

        value = self._secrets.get(key)
        if value is None:
            return ActionResult(success=False, error=f"Secret '{key}' not found")
        return ActionResult(success=True, data={"key": key, "value": value})

    def _list_keys(self) -> ActionResult:
        if not self.unlocked:
            return ActionResult(success=False, error="Vault is locked")
        keys = list(self._secrets.keys())
        return ActionResult(success=True, data={"keys": keys})

    def _set(self, key: str, value) -> ActionResult:
        if not self.unlocked:
            return ActionResult(success=False, error="Vault is locked")
        if not key:
            return ActionResult(success=False, error="Key is required")

        self._secrets[key] = str(value) if value is not None else ""
        return ActionResult(success=True, data={"key": key, "value": self._secrets[key]})

    def _delete(self, key: str) -> ActionResult:
        if not self.unlocked:
            return ActionResult(success=False, error="Vault is locked")
        if not key:
            return ActionResult(success=False, error="Key is required")

        if key not in self._secrets:
            return ActionResult(success=False, error=f"Secret '{key}' not found")

        del self._secrets[key]
        return ActionResult(success=True, data={"deleted_key": key})

    def _save(self, confirm_key: str = "") -> ActionResult:
        if not self.unlocked:
            return ActionResult(success=False, error="Vault is locked")
        
        if self._secrets is None:
            return ActionResult(success=False, error="Vault state is invalid")
        
        # If confirm_key provided, validate it
        if confirm_key and confirm_key != self._confirm_key:
            return ActionResult(success=False, error="Invalid confirmation key")

        try:
            blob = encrypt(self._secrets, self._master_key)
            if not blob:
                return ActionResult(success=False, error="Encryption produced empty blob")
            self._store.save(blob)
            return ActionResult(success=True, data={"saved": True, "count": len(self._secrets)})
        except (RuntimeError, ValueError) as e:
            return ActionResult(success=False, error=str(e))

    def _lock(self) -> ActionResult:
        self._secrets = None
        return ActionResult(success=True, data={"locked": True})

    def _status(self) -> ActionResult:
        return ActionResult(
            success=True,
            data={
                "unlocked": self.unlocked,
                "vault_exists": self.vault_exists,
                "env_exists": self.env_exists,
                "ready": self.vault_exists and bool(self._master_key),
            },
        )

    def _bootstrap(self) -> ActionResult:
        """
        First-run setup. Generates fresh master/confirm keys, writes them to the
        configured env file, and creates an empty encrypted vault on disk. The
        vault stays locked afterwards so the user must enter the master key to
        proceed (gives them a beat to save the keys somewhere safe).
        """
        if self.vault_exists and self.env_exists:
            return ActionResult(success=False, error="Vault already initialized")
        if not self._env_path:
            return ActionResult(success=False, error="No env_path configured for vault")

        master = generate_key()
        confirm = generate_key()
        try:
            self._write_env_file(self._env_path, master, confirm)
            blob = encrypt({}, master)
            self._store.save(blob)
        except (RuntimeError, OSError) as e:
            return ActionResult(success=False, error=f"Bootstrap failed: {e}")

        self._master_key = master
        self._confirm_key = confirm
        self._secrets = None  # leave locked — user must unlock with the master key
        return ActionResult(
            success=True,
            data={"master_key": master, "confirm_key": confirm},
        )

    # ── env file helpers ──────────────────────────────────────────────────

    @staticmethod
    def _read_env_file(path: str) -> tuple[str, str]:
        """Parse VAULT_MASTER_KEY / VAULT_CONFIRM_KEY out of a KEY=VALUE file."""
        master = confirm = ""
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "VAULT_MASTER_KEY":
                    master = value
                elif key == "VAULT_CONFIRM_KEY":
                    confirm = value
        return master, confirm

    @staticmethod
    def _write_env_file(path: str, master: str, confirm: str) -> None:
        """Write the two keys to an env file, creating parent dirs if needed."""
        directory = os.path.dirname(path) or "."
        Path(directory).mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"VAULT_MASTER_KEY={master}\n")
            f.write(f"VAULT_CONFIRM_KEY={confirm}\n")
