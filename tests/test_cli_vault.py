# tests/test_cli_vault.py
from pathlib import Path
import pytest


def _bootstrap_vault(vault_path: str, env_path: str) -> str:
    """Create a fresh vault and return the generated master key."""
    from lib.security.crypto import generate_key
    from lib.security.vault_service import VaultService
    from lib.security.vault_store import VaultStore
    from lib.contracts.base import ActionRequest

    master_key = generate_key()
    Path(env_path).parent.mkdir(parents=True, exist_ok=True)
    Path(env_path).write_text(
        f"VAULT_MASTER_KEY={master_key}\nVAULT_CONFIRM_KEY={master_key}\n"
    )
    service = VaultService(
        store=VaultStore(path=vault_path),
        master_key=master_key,
        confirm_key=master_key,
        env_path=env_path,
    )
    service.execute(ActionRequest(action="unlock"))
    service.execute(ActionRequest(action="save", data={}))
    return master_key


def test_encrypt_to_vault_roundtrip(tmp_path):
    vault_path = str(tmp_path / "vault.json")
    env_path = str(tmp_path / ".env")
    _bootstrap_vault(vault_path, env_path)

    from lib.config.cli import _encrypt_to_vault
    _encrypt_to_vault(
        {"DB_URL": "sqlite:///test.db", "API_KEY": "abc123"},
        vault_path=vault_path,
        env_path=env_path,
    )

    from lib.security.vault import open_vault
    vault = open_vault(vault_path=vault_path, env_path=env_path)
    assert vault.get("DB_URL") == "sqlite:///test.db"
    assert vault.get("API_KEY") == "abc123"


def test_encrypt_to_vault_adds_to_existing(tmp_path):
    vault_path = str(tmp_path / "vault.json")
    env_path = str(tmp_path / ".env")
    _bootstrap_vault(vault_path, env_path)

    from lib.config.cli import _encrypt_to_vault
    _encrypt_to_vault({"KEY1": "val1"}, vault_path=vault_path, env_path=env_path)
    _encrypt_to_vault({"KEY2": "val2"}, vault_path=vault_path, env_path=env_path)

    from lib.security.vault import open_vault
    vault = open_vault(vault_path=vault_path, env_path=env_path)
    assert vault.get("KEY1") == "val1"
    assert vault.get("KEY2") == "val2"


def test_flex_decrypt_prints_keys(tmp_path, monkeypatch, capsys):
    vault_path = str(tmp_path / "vault.json")
    env_path = str(tmp_path / ".env")
    _bootstrap_vault(vault_path, env_path)

    from lib.config.cli import _encrypt_to_vault
    _encrypt_to_vault({"MYKEY": "myval"}, vault_path=vault_path, env_path=env_path)

    monkeypatch.setenv("VAULT_PATH", vault_path)
    monkeypatch.setenv("VAULT_ENV_PATH", env_path)

    from lib.config.cli import flex_decrypt
    flex_decrypt()
    out = capsys.readouterr().out
    assert "MYKEY" in out
    assert "myval" in out
