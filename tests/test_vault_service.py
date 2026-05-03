"""VaultService tests — encryption, decryption, actions."""
import os
import pytest
from lib.contracts.base import ActionRequest
from lib.security.vault_service import VaultService
from lib.security.vault_store import VaultStore
from lib.security.crypto import generate_key


@pytest.fixture
def temp_vault(tmp_path):
    """Temporary vault file path."""
    vault_path = tmp_path / ".secrets" / "vault.json"
    return str(vault_path)


@pytest.fixture
def vault_keys():
    """Generate unique keys for each test."""
    return {"master": generate_key(), "confirm": generate_key()}


def test_status_vault_does_not_exist(temp_vault, vault_keys):
    """New vault is locked and file doesn't exist."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    result = service.execute(ActionRequest(action="status"))

    assert result.success is True
    assert result.data["unlocked"] is False
    assert result.data["vault_exists"] is False


def test_unlock_creates_vault_on_first_run(temp_vault, vault_keys):
    """Unlock with correct key creates vault file on first run."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    result = service.execute(
        ActionRequest(action="unlock", data={"key": vault_keys["master"]})
    )

    assert result.success is True
    assert result.data["unlocked"] is True
    assert result.data["is_first_run"] is True
    assert store.exists() is True


def test_unlock_wrong_key_returns_failure(temp_vault, vault_keys):
    """Unlock with wrong key fails."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    # Create vault first
    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))

    # Try to unlock with wrong key
    result = service.execute(ActionRequest(action="unlock", data={"key": "wrong_key"}))

    assert result.success is False
    assert "key" in result.error.lower()


def test_get_requires_unlock(temp_vault, vault_keys):
    """Get fails when vault is locked."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    result = service.execute(ActionRequest(action="get", data={"key": "DB_PASSWORD"}))

    assert result.success is False
    assert "locked" in result.error.lower()


def test_set_and_get_roundtrip(temp_vault, vault_keys):
    """Set and get same value."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))

    set_result = service.execute(
        ActionRequest(action="set", data={"key": "DB_PASSWORD", "value": "secret123"})
    )
    assert set_result.success is True

    get_result = service.execute(ActionRequest(action="get", data={"key": "DB_PASSWORD"}))
    assert get_result.success is True
    assert get_result.data["value"] == "secret123"


def test_list_keys_never_returns_values(temp_vault, vault_keys):
    """List keys returns only key names, not values."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    service.execute(
        ActionRequest(action="set", data={"key": "SECRET1", "value": "hidden1"})
    )
    service.execute(
        ActionRequest(action="set", data={"key": "SECRET2", "value": "hidden2"})
    )

    result = service.execute(ActionRequest(action="list_keys"))

    assert result.success is True
    assert "SECRET1" in result.data["keys"]
    assert "SECRET2" in result.data["keys"]
    assert "hidden1" not in str(result.data["keys"])
    assert "hidden2" not in str(result.data["keys"])


def test_save_wrong_confirm_key(temp_vault, vault_keys):
    """Save with wrong confirmation key fails."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    service.execute(
        ActionRequest(action="set", data={"key": "DB_PASSWORD", "value": "secret"})
    )

    result = service.execute(
        ActionRequest(action="save", data={"confirm_key": "wrong_confirm"})
    )

    assert result.success is False
    assert "confirmation" in result.error.lower() or "key" in result.error.lower()


def test_save_persists_to_disk(temp_vault, vault_keys):
    """Save persists to disk, new instance reads same data."""
    store1 = VaultStore(temp_vault)
    service1 = VaultService(store1, vault_keys["master"], vault_keys["confirm"])

    service1.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    service1.execute(
        ActionRequest(action="set", data={"key": "DB_PASSWORD", "value": "secret123"})
    )
    service1.execute(
        ActionRequest(action="save", data={"confirm_key": vault_keys["confirm"]})
    )

    # New instance reads same vault
    store2 = VaultStore(temp_vault)
    service2 = VaultService(store2, vault_keys["master"], vault_keys["confirm"])
    service2.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))

    result = service2.execute(ActionRequest(action="get", data={"key": "DB_PASSWORD"}))

    assert result.success is True
    assert result.data["value"] == "secret123"


def test_lock_clears_memory(temp_vault, vault_keys):
    """Lock clears in-memory state, subsequent get fails."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    service.execute(
        ActionRequest(action="set", data={"key": "DB_PASSWORD", "value": "secret"})
    )

    lock_result = service.execute(ActionRequest(action="lock"))
    assert lock_result.success is True

    get_result = service.execute(ActionRequest(action="get", data={"key": "DB_PASSWORD"}))
    assert get_result.success is False
    assert "locked" in get_result.error.lower()


def test_bootstrap_creates_env_and_vault(tmp_path):
    """First-run bootstrap writes both .env and vault.json, returns the keys."""
    vault_path = str(tmp_path / ".secrets" / "vault.json")
    env_path = str(tmp_path / ".secrets" / ".env")
    store = VaultStore(vault_path)
    service = VaultService(store, env_path=env_path)

    # Nothing on disk yet, status reports not-ready
    status = service.execute(ActionRequest(action="status"))
    assert status.data["ready"] is False
    assert status.data["env_exists"] is False
    assert status.data["vault_exists"] is False

    result = service.execute(ActionRequest(action="bootstrap"))

    assert result.success is True
    master = result.data["master_key"]
    confirm = result.data["confirm_key"]
    assert master and confirm and master != confirm
    assert os.path.isfile(env_path)
    assert os.path.isfile(vault_path)

    # The newly-bootstrapped service can unlock with the returned master key
    unlocked = service.execute(ActionRequest(action="unlock", data={"key": master}))
    assert unlocked.success is True

    # A fresh service instance loads the same keys from .secrets/.env
    fresh = VaultService(VaultStore(vault_path), env_path=env_path)
    again = fresh.execute(ActionRequest(action="unlock", data={"key": master}))
    assert again.success is True


def test_bootstrap_refuses_when_already_initialized(tmp_path):
    """Bootstrap is a one-shot — it won't overwrite an existing vault."""
    vault_path = str(tmp_path / ".secrets" / "vault.json")
    env_path = str(tmp_path / ".secrets" / ".env")
    service = VaultService(VaultStore(vault_path), env_path=env_path)

    first = service.execute(ActionRequest(action="bootstrap"))
    assert first.success is True

    second = service.execute(ActionRequest(action="bootstrap"))
    assert second.success is False
    assert "already" in second.error.lower()


def test_delete_removes_key(temp_vault, vault_keys):
    """Delete removes key from vault."""
    store = VaultStore(temp_vault)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    service.execute(
        ActionRequest(action="set", data={"key": "DB_PASSWORD", "value": "secret"})
    )

    delete_result = service.execute(
        ActionRequest(action="delete", data={"key": "DB_PASSWORD"})
    )
    assert delete_result.success is True

    get_result = service.execute(ActionRequest(action="get", data={"key": "DB_PASSWORD"}))
    assert get_result.success is False
    assert "not found" in get_result.error.lower()


def test_full_round_trip_with_fake_dict(temp_vault, vault_keys):
    """Full workflow: add multiple secrets, save, close, reopen, retrieve all."""
    # Fake "database" of secrets the user wants to store
    fake_secrets = {
        "db_password": "super_secret_123",
        "api_key": "sk_live_abc123xyz",
        "slack_webhook": "https://hooks.slack.com/...",
        "openai_key": "sk_org_openai_key_here",
    }

    # First instance: add all secrets
    store1 = VaultStore(temp_vault)
    service1 = VaultService(store1, vault_keys["master"], vault_keys["confirm"])

    service1.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))

    # Add all secrets from fake dict
    for key, value in fake_secrets.items():
        result = service1.execute(
            ActionRequest(action="set", data={"key": key, "value": value})
        )
        assert result.success is True, f"Failed to set {key}"

    # Verify all are retrievable before saving
    for key, expected_value in fake_secrets.items():
        result = service1.execute(ActionRequest(action="get", data={"key": key}))
        assert result.success is True
        assert result.data["value"] == expected_value

    # Save to disk (without confirmation key — now optional)
    save_result = service1.execute(ActionRequest(action="save", data={}))
    assert save_result.success is True
    assert save_result.data["count"] == len(fake_secrets)

    # Lock the first instance
    service1.execute(ActionRequest(action="lock"))

    # Second instance: reopen and verify all secrets persist
    store2 = VaultStore(temp_vault)
    service2 = VaultService(store2, vault_keys["master"], vault_keys["confirm"])

    service2.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))

    # List all keys
    list_result = service2.execute(ActionRequest(action="list_keys"))
    assert list_result.success is True
    stored_keys = set(list_result.data["keys"])
    assert stored_keys == set(fake_secrets.keys())

    # Retrieve each secret and verify value matches fake dict
    for key, expected_value in fake_secrets.items():
        result = service2.execute(ActionRequest(action="get", data={"key": key}))
        assert result.success is True, f"Failed to get {key}"
        assert result.data["value"] == expected_value, f"Value mismatch for {key}"

    # Verify total count matches
    all_values = [
        service2.execute(ActionRequest(action="get", data={"key": k})).data["value"]
        for k in fake_secrets.keys()
    ]
    assert len(all_values) == len(fake_secrets)
