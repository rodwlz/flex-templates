"""CLI commands for vault management.

Entry points (configured in pyproject.toml [project.scripts]):
    flex-encrypt  — interactively write secrets into the encrypted vault
    flex-decrypt  — print all secrets to stdout (DEVELOPMENT USE ONLY)

Both commands read VAULT_PATH and VAULT_ENV_PATH from environment variables,
falling back to the default .secrets/ locations.
"""
import os
import sys


def _encrypt_to_vault(secrets: dict[str, str], *, vault_path: str, env_path: str) -> None:
    """Write *secrets* into the vault and persist to disk.

    Requires the vault to already be initialized (vault.json + .env with keys).
    Call the /security view in the app on first run to bootstrap.
    """
    from lib.security.vault import open_vault
    vault = open_vault(vault_path=vault_path, env_path=env_path)
    for key, value in secrets.items():
        vault.set(key, value)
    vault.save()


def flex_encrypt() -> None:
    """flex-encrypt — interactively write secrets into the encrypted vault."""
    vault_path = os.getenv("VAULT_PATH", ".secrets/vault.json")
    env_path = os.getenv("VAULT_ENV_PATH", ".secrets/.env")
    print(f"Vault: {vault_path}")
    print("Enter secrets one at a time. Leave KEY empty to finish.\n")
    secrets: dict[str, str] = {}
    while True:
        key = input("KEY: ").strip()
        if not key:
            break
        value = input(f"VALUE for {key!r}: ").strip()
        secrets[key] = value
    if not secrets:
        print("No secrets entered. Nothing saved.")
        return
    try:
        _encrypt_to_vault(secrets, vault_path=vault_path, env_path=env_path)
        print(f"\n{len(secrets)} secret(s) saved to {vault_path}")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def flex_decrypt() -> None:
    """flex-decrypt — print all vault secrets to stdout.

    WARNING: only use this in development. Never run in production.
    """
    vault_path = os.getenv("VAULT_PATH", ".secrets/vault.json")
    env_path = os.getenv("VAULT_ENV_PATH", ".secrets/.env")
    print("WARNING: printing secrets — development use only\n")
    try:
        from lib.security.vault import open_vault
        vault = open_vault(vault_path=vault_path, env_path=env_path)
        keys = vault.keys()
        if not keys:
            print("(vault is empty)")
            return
        width = max(len(k) for k in keys)
        for k in sorted(keys):
            print(f"{k:{width}} = {vault.get(k)}")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
