# Vault Usage Guide

The vault is an encrypted secrets manager built into the framework. Use it to store and retrieve sensitive data like database passwords, API keys, and credentials without hardcoding them.

## Quick Start

**Retrieve a secret from any service:**

```python
from lib.contracts.base import ActionRequest
from lib.security import vault_service

result = vault_service.execute(
    ActionRequest(action="get", data={"key": "db_password"})
)

if result.success:
    password = result.data["value"]
    # Use the password to connect to database...
else:
    raise RuntimeError(f"Failed to get secret: {result.error}")
```

**Simple example: Print POSTGRES_USER from vault**

```python
from lib.contracts.base import ActionRequest

# Assuming you have vault_service (passed via props or injected)
result = vault_service.execute(
    ActionRequest(action="get", data={"key": "POSTGRES_USER"})
)

if result.success:
    postgres_user = result.data["value"]
    print(f"Database user: {postgres_user}")
else:
    print(f"Error: {result.error}")
    # Common errors:
    # "Vault is locked" — User hasn't entered master key yet
    # "Secret 'POSTGRES_USER' not found" — Key doesn't exist in vault
```

**Test it in a view:**

```python
# lib/views/test_vault.py
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest

class TestVaultView(BaseView):
    title = "Test Vault"
    
    def build_content(self):
        # Get POSTGRES_USER from vault
        result = self._vault_service.execute(
            ActionRequest(action="get", data={"key": "POSTGRES_USER"})
        )
        
        if result.success:
            user_text = f"✓ POSTGRES_USER: {result.data['value']}"
            color = ft.Colors.GREEN
        else:
            user_text = f"✗ Error: {result.error}"
            color = ft.Colors.RED
        
        return ft.Column([
            ft.Text("Vault Test", size=18, weight="bold"),
            ft.Text(user_text, color=color, size=14),
        ])

def view(page, props):
    return TestVaultView(page, props).render()
```

Navigate to `/test_vault` and you'll see the value printed!


## Architecture

The vault stores encrypted key-value pairs in `.secrets/vault.json`:
- **Encrypted on disk** — `.secrets/vault.json` is useless without the master key
- **Decrypted in RAM only** — secrets live in memory while unlocked, never written unencrypted
- **Two-key design**:
  - **Master Key** (`VAULT_MASTER_KEY` in `.secrets/.env`) — required to unlock and read/write secrets
  - **Confirmation Key** (`VAULT_CONFIRM_KEY` in `.secrets/.env`) — required to persist changes to disk (prevents accidents)

## Vault Service API

The vault implements the `IService` contract. All operations use `execute(ActionRequest)`:

### Actions

#### `get` — Retrieve a single secret

```python
result = vault_service.execute(
    ActionRequest(action="get", data={"key": "api_key"})
)

# result.success: bool
# result.data: {"key": "api_key", "value": "sk_live_..."}
# result.error: str (if failed, e.g., "Vault is locked", "Secret 'api_key' not found")
```

**Errors:**
- `"Vault is locked"` — User hasn't unlocked it yet (entered master key)
- `"Secret '<key>' not found"` — Key doesn't exist in vault
- `"Key is required"` — Empty key string

#### `list_keys` — Get all secret names (not values)

```python
result = vault_service.execute(ActionRequest(action="list_keys"))

# result.data: {"keys": ["db_password", "api_key", "slack_webhook"]}
```

**Errors:**
- `"Vault is locked"` — Can't list if vault isn't unlocked

#### `set` — Add or update a secret (in memory only)

```python
result = vault_service.execute(
    ActionRequest(action="set", data={"key": "db_password", "value": "secret123"})
)

# result.success: bool
# result.data: {"key": "db_password", "value": "secret123"}
```

**Note:** This updates the in-memory vault only. Changes aren't persisted to disk until `save` is called.

**Errors:**
- `"Vault is locked"` — Can't modify locked vault
- `"Key is required"` — Empty key

#### `delete` — Remove a secret (in memory only)

```python
result = vault_service.execute(
    ActionRequest(action="delete", data={"key": "old_api_key"})
)

# result.data: {"deleted_key": "old_api_key"}
```

**Errors:**
- `"Vault is locked"` — Can't modify locked vault
- `"Secret '<key>' not found"` — Key doesn't exist

#### `save` — Persist all changes to disk

```python
# Save without confirmation key (works if confirm_key not set or empty)
result = vault_service.execute(ActionRequest(action="save", data={}))

# Or with confirmation key for extra security
result = vault_service.execute(
    ActionRequest(action="save", data={"confirm_key": "my_confirm_key"})
)

# result.data: {"saved": True, "count": 5}  (5 = number of secrets saved)
```

**Errors:**
- `"Vault is locked"` — Can't save if vault isn't unlocked
- `"Invalid confirmation key"` — confirm_key doesn't match `VAULT_CONFIRM_KEY` from env
- Encryption/file errors

#### `unlock` — Decrypt vault with master key

```python
result = vault_service.execute(
    ActionRequest(action="unlock", data={"key": "my_master_key"})
)

# result.data: {"unlocked": True, "is_first_run": False}
```

This is usually called by the Security view, but services can call it too if needed.

**Errors:**
- `"Invalid master key"` — Key doesn't match `VAULT_MASTER_KEY`

#### `lock` — Clear the decrypted vault from memory

```python
result = vault_service.execute(ActionRequest(action="lock"))

# result.data: {"locked": True}
```

After this, `get`/`set`/`delete` will fail until `unlock` is called again.

#### `status` — Check vault readiness and lock state

```python
result = vault_service.execute(ActionRequest(action="status"))

# result.data: {
#     "unlocked": True,           # bool: is vault currently decrypted in memory?
#     "vault_exists": True,       # bool: does .secrets/vault.json exist?
#     "env_exists": True,         # bool: does .secrets/.env exist?
#     "ready": True,              # bool: vault_exists AND master_key is set?
# }
```

Use this to check if the vault is ready before operations.

## Real-World Examples

### Database Connection Service

```python
# lib/services/database_service.py
from lib.contracts.base import ActionRequest, ActionResult
from lib.core.interfaces import IService

class DatabaseService(IService):
    def __init__(self, vault_service, db_type="postgres"):
        self.vault_service = vault_service
        self.db_type = db_type
        self.connection = None

    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "connect":
                return self._connect()
            case "query":
                return self._query(request.data.get("sql"))
            case _:
                return ActionResult(success=False, error=f"Unknown action: {request.action}")

    def _connect(self) -> ActionResult:
        """Pull DB credentials from vault and connect."""
        # Get password from vault
        pw_result = self.vault_service.execute(
            ActionRequest(action="get", data={"key": "db_password"})
        )
        if not pw_result.success:
            return ActionResult(success=False, error=f"DB password not in vault: {pw_result.error}")

        # Get username from vault
        user_result = self.vault_service.execute(
            ActionRequest(action="get", data={"key": "db_user"})
        )
        if not user_result.success:
            return ActionResult(success=False, error=f"DB user not in vault: {user_result.error}")

        try:
            import psycopg2
            self.connection = psycopg2.connect(
                database="mydb",
                user=user_result.data["value"],
                password=pw_result.data["value"],
                host="localhost",
                port="5432"
            )
            return ActionResult(success=True, data={"connected": True})
        except Exception as e:
            return ActionResult(success=False, error=f"Connection failed: {e}")

    def _query(self, sql: str) -> ActionResult:
        if not self.connection:
            return ActionResult(success=False, error="Not connected")
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return ActionResult(success=True, data={"rows": rows})
        except Exception as e:
            return ActionResult(success=False, error=str(e))
```

### API Client Service

```python
# lib/services/slack_service.py
from lib.contracts.base import ActionRequest, ActionResult
from lib.core.interfaces import IService
import requests

class SlackService(IService):
    def __init__(self, vault_service):
        self.vault_service = vault_service

    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "send_message":
                return self._send_message(request.data.get("text"))
            case _:
                return ActionResult(success=False, error=f"Unknown action: {request.action}")

    def _send_message(self, text: str) -> ActionResult:
        """Send a message to Slack using webhook from vault."""
        webhook_result = self.vault_service.execute(
            ActionRequest(action="get", data={"key": "slack_webhook"})
        )
        if not webhook_result.success:
            return ActionResult(success=False, error=f"Slack webhook not in vault")

        webhook_url = webhook_result.data["value"]
        try:
            response = requests.post(webhook_url, json={"text": text})
            response.raise_for_status()
            return ActionResult(success=True, data={"sent": True})
        except Exception as e:
            return ActionResult(success=False, error=str(e))
```

### In a View (React to User Input)

```python
# lib/views/my_view.py
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest

class MyView(BaseView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._vault_service = props["vault_service"]

    def _fetch_user_data(self, e):
        """Fetch data using credentials from vault."""
        # Get API key from vault
        result = self._vault_service.execute(
            ActionRequest(action="get", data={"key": "api_key"})
        )

        if not result.success:
            self._error_text.value = f"API key not found in vault: {result.error}"
            self._error_text.update()
            return

        api_key = result.data["value"]

        # Use the API key to make a request
        import requests
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get("https://api.example.com/user", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            self._show_data(data)
        except Exception as ex:
            self._error_text.value = f"Request failed: {ex}"
            self._error_text.update()

    def build_content(self):
        # ... build UI with button that calls _fetch_user_data
        pass
```

## State Machine

The vault has three states:

```
┌─────────────┐
│   LOCKED    │  Vault file exists, decrypted state cleared from RAM
└──────┬──────┘
       │ unlock(master_key)
       │ ↓
┌─────────────┐
│  UNLOCKED   │  Secrets decrypted in RAM, can get/set/delete
└──────┬──────┘
       │ lock() or app closes
       │ ↓
┌─────────────┐
│   LOCKED    │  Secrets cleared from memory, vault.json untouched on disk
└─────────────┘
```

**First run (no `.secrets/` folder):**
1. Security view auto-bootstraps
2. Generates fresh master + confirm keys
3. Creates `.secrets/.env` and `.secrets/vault.json`
4. Shows keys to user → they copy them somewhere safe
5. User clicks "Continue" → goes to unlock form
6. User enters the master key they just saw
7. Vault unlocks → password manager is ready

## Error Handling

Always check `result.success`:

```python
result = vault_service.execute(ActionRequest(action="get", data={"key": "password"}))

if result.success:
    password = result.data["value"]
    # Use it...
else:
    # Handle error
    if "locked" in result.error.lower():
        print("Vault is locked, ask user to unlock")
    elif "not found" in result.error.lower():
        print(f"Secret not in vault")
    else:
        print(f"Vault error: {result.error}")
```

## Security Notes

- **Master key** (`VAULT_MASTER_KEY` in `.secrets/.env`) is the only way to decrypt the vault. Lose it, lose your secrets.
- **Confirmation key** (`VAULT_CONFIRM_KEY`) prevents accidental overwrites. It's optional for the save action but recommended.
- Secrets are **never logged or printed** — treat them like passwords.
- `.secrets/` folder is in `.gitignore` — never commit it.
- The encrypted vault.json is safe to commit (useless without the keys).

## Testing Secrets

Use `test_vault_service.py` as a reference. The test suite includes:
- Full round-trip: add → save → reopen → retrieve
- Error cases: locked vault, missing keys, wrong keys
- Persistence: verify secrets survive a new vault instance

```python
# Example test
def test_get_secret_after_save(tmp_path, vault_keys):
    """Add secret, save, reopen, verify it's there."""
    vault_path = str(tmp_path / "vault.json")
    store = VaultStore(vault_path)
    service = VaultService(store, vault_keys["master"], vault_keys["confirm"])

    service.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    service.execute(ActionRequest(action="set", data={"key": "api_key", "value": "sk_123"}))
    service.execute(ActionRequest(action="save", data={}))

    # New instance, same vault
    service2 = VaultService(VaultStore(vault_path), vault_keys["master"], vault_keys["confirm"])
    service2.execute(ActionRequest(action="unlock", data={"key": vault_keys["master"]}))
    result = service2.execute(ActionRequest(action="get", data={"key": "api_key"}))

    assert result.success
    assert result.data["value"] == "sk_123"
```
