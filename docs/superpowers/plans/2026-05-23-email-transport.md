# Email Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make password-reset email pluggable — `ConsoleSender` works out of the box in dev (prints token to stdout), `SmtpSender` drops in for production (Proxmox/Mailcow/any SMTP) via one line in `main.py`.

**Architecture:** `IEmailSender` ABC in `lib/core/interfaces.py`. Two concrete implementations in `lib/email/`. `UserService` receives the sender via constructor injection (defaults to `ConsoleSender`). Token removed from `forgot-password` HTTP response body. `AppConfig` gains SMTP config fields — all read from `.secrets/.env`.

**Tech Stack:** Python `smtplib` (stdlib only — no new packages), `pydantic-settings` (already installed), pytest `capsys` for console capture, `unittest.mock` for SMTP.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `lib/core/interfaces.py` | Modify | Add `IEmailSender` ABC |
| `lib/email/__init__.py` | Create | Empty package marker |
| `lib/email/console_sender.py` | Create | Dev sender — prints to stdout |
| `lib/email/smtp_sender.py` | Create | Production sender — real SMTP via smtplib |
| `lib/config/settings.py` | Modify | Add email/SMTP config fields |
| `lib/services/user_service.py` | Modify | Inject `IEmailSender`; update `request_reset` |
| `main.py` | Modify | Instantiate sender; pass to `UserService` |
| `tests/test_email_senders.py` | Create | ConsoleSender + SmtpSender unit tests |
| `tests/test_auth_gaps.py` | Modify | Update `forgot-password` response assertion |
| `tests/test_smoke.py` | Modify | Add `lib.email.*` module imports |

---

## Task 1: `IEmailSender` Interface + `ConsoleSender`

**Files:**
- Modify: `lib/core/interfaces.py`
- Create: `lib/email/__init__.py`
- Create: `lib/email/console_sender.py`
- Create: `tests/test_email_senders.py`

- [ ] **Step 1: Write a failing test**

Create `tests/test_email_senders.py`:

```python
from lib.email.console_sender import ConsoleSender


def test_console_sender_prints_to_stdout(capsys):
    sender = ConsoleSender()
    sender.send(to="bob@example.com", subject="Test", body="Hello Bob")
    out = capsys.readouterr().out
    assert "bob@example.com" in out
    assert "Test" in out
    assert "Hello Bob" in out


def test_console_sender_implements_interface():
    from lib.core.interfaces import IEmailSender
    assert isinstance(ConsoleSender(), IEmailSender)
```

- [ ] **Step 2: Run to see failures**

```
pytest tests/test_email_senders.py -v
```
Expected: `ImportError: cannot import name 'ConsoleSender'`

- [ ] **Step 3: Add `IEmailSender` to `lib/core/interfaces.py`**

Append at the end of `lib/core/interfaces.py` (after `IFlexComponent`):

```python
class IEmailSender(ABC):
    """Send a single email message. Implementations: ConsoleSender (dev), SmtpSender (prod)."""

    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> None: ...
```

- [ ] **Step 4: Create `lib/email/__init__.py`**

Empty file:
```python
```

- [ ] **Step 5: Create `lib/email/console_sender.py`**

```python
from lib.core.interfaces import IEmailSender


class ConsoleSender(IEmailSender):
    """Dev email sender — prints message to stdout. Zero dependencies."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        print(f"\n[EMAIL] To: {to}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body:\n{body}\n")
```

- [ ] **Step 6: Run the tests**

```
pytest tests/test_email_senders.py -v
```
Expected: both tests PASS

- [ ] **Step 7: Commit**

```
git add lib/core/interfaces.py lib/email/__init__.py lib/email/console_sender.py tests/test_email_senders.py
git commit -m "feat: add IEmailSender interface and ConsoleSender"
```

---

## Task 2: `SmtpSender`

**Files:**
- Create: `lib/email/smtp_sender.py`
- Modify: `tests/test_email_senders.py`

- [ ] **Step 1: Write failing SmtpSender tests**

Append to `tests/test_email_senders.py`:

```python
from unittest.mock import MagicMock, patch
from lib.email.smtp_sender import SmtpSender


def _mock_config(port=587):
    cfg = MagicMock()
    cfg.smtp_host     = "smtp.example.com"
    cfg.smtp_port     = port
    cfg.smtp_username = "user@example.com"
    cfg.smtp_password = "secret"
    cfg.smtp_from     = "noreply@example.com"
    return cfg


def test_smtp_sender_implements_interface():
    from lib.core.interfaces import IEmailSender
    assert isinstance(SmtpSender(_mock_config()), IEmailSender)


def test_smtp_sender_calls_sendmail_on_port_587():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        mock_smtp_cls.return_value.__exit__  = MagicMock(return_value=False)

        SmtpSender(_mock_config(port=587)).send(
            to="alice@example.com", subject="Hi", body="Hello"
        )
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "secret")
        mock_smtp.sendmail.assert_called_once()
        args = mock_smtp.sendmail.call_args[0]
        assert args[0] == "noreply@example.com"
        assert args[1] == "alice@example.com"


def test_smtp_sender_uses_ssl_on_port_465():
    with patch("smtplib.SMTP_SSL") as mock_ssl_cls:
        mock_smtp = MagicMock()
        mock_ssl_cls.return_value.__enter__ = lambda s: mock_smtp
        mock_ssl_cls.return_value.__exit__  = MagicMock(return_value=False)

        SmtpSender(_mock_config(port=465)).send(
            to="alice@example.com", subject="Hi", body="Hello"
        )
        mock_smtp.login.assert_called_once()
        mock_smtp.sendmail.assert_called_once()
```

- [ ] **Step 2: Run to see failures**

```
pytest tests/test_email_senders.py -v -k smtp
```
Expected: `ImportError: cannot import name 'SmtpSender'`

- [ ] **Step 3: Create `lib/email/smtp_sender.py`**

```python
import smtplib
from email.mime.text import MIMEText

from lib.core.interfaces import IEmailSender


class SmtpSender(IEmailSender):
    """Production email sender — sends via SMTP. Configure in .secrets/.env."""

    def __init__(self, config):
        self._host     = config.smtp_host
        self._port     = config.smtp_port
        self._username = config.smtp_username
        self._password = config.smtp_password
        self._from     = config.smtp_from

    def send(self, *, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = self._from
        msg["To"]      = to

        if self._port == 465:
            ctx = smtplib.SMTP_SSL(self._host, self._port)
        else:
            ctx = smtplib.SMTP(self._host, self._port)

        with ctx as smtp:
            if self._port != 465:
                smtp.starttls()
            smtp.login(self._username, self._password)
            smtp.sendmail(self._from, to, msg.as_string())
```

- [ ] **Step 4: Run all email tests**

```
pytest tests/test_email_senders.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```
git add lib/email/smtp_sender.py tests/test_email_senders.py
git commit -m "feat: add SmtpSender (STARTTLS port 587 / SSL port 465)"
```

---

## Task 3: AppConfig SMTP Fields

**Files:**
- Modify: `lib/config/settings.py`

- [ ] **Step 1: Add email/SMTP fields to `AppConfig`**

Open `lib/config/settings.py`. Add the following fields inside the `AppConfig` class, after the existing vault fields:

```python
# ── Email transport ────────────────────────────────────────────────────────
email_sender:   str = "console"              # "console" | "smtp"
smtp_host:      str = ""
smtp_port:      int = 587
smtp_username:  str = ""
smtp_password:  str = ""                     # set in vault / .secrets/.env for prod
smtp_from:      str = "noreply@example.com"
```

These fields read from `.secrets/.env` automatically (same `env_file` as all other config). No other changes to `settings.py` needed.

- [ ] **Step 2: Verify config loads without error**

```
python -c "from lib.config.settings import AppConfig; c = AppConfig(); print(c.email_sender)"
```
Expected: `console`

- [ ] **Step 3: Commit**

```
git add lib/config/settings.py
git commit -m "feat: add email/SMTP config fields to AppConfig"
```

---

## Task 4: Inject `IEmailSender` into `UserService`

**Files:**
- Modify: `lib/services/user_service.py`

- [ ] **Step 1: Write a failing test for the new `request_reset` response shape**

Add to `tests/test_auth_gaps.py` (below the existing forgot-password tests):

```python
def test_forgot_password_response_has_message_not_token(auth_client):
    """Token must NOT appear in the response body after email sender is injected."""
    client, repo = auth_client
    _seed_user(repo, "charlie")
    resp = client.post("/v1/auth/forgot-password", json={"email": "charlie@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" not in body
    assert "message" in body
    assert "expires_in" in body
```

Run it — it should FAIL because `request_reset` still returns `{"token": ..., "expires_in": 900}`:

```
pytest tests/test_auth_gaps.py::test_forgot_password_response_has_message_not_token -v
```
Expected: FAIL (token is in body)

- [ ] **Step 2: Update `UserService.__init__` to accept `email_sender`**

In `lib/services/user_service.py`, change the `__init__` method:

```python
def __init__(self, factory: SessionFactory, email_sender=None):
    super().__init__(factory)
    if email_sender is None:
        from lib.email.console_sender import ConsoleSender
        email_sender = ConsoleSender()
    self._email_sender = email_sender
```

- [ ] **Step 3: Update `request_reset` in `UserService`**

Replace the existing `request_reset` method:

```python
def request_reset(self, data: dict) -> dict:
    """Request a password reset token. Sends email (console in dev, SMTP in prod)."""
    email = data.get("email", "")
    if not email:
        raise ValueError("email is required")

    repo = UserRepository(self._factory)
    token_repo = PasswordResetTokenRepository(self._factory)

    users = repo.filter_by(email=email)
    if not users:
        return {
            "message": "If that email is registered, a reset email has been sent",
            "expires_in": 900,
        }

    user_id = users[0]["id"]   # uuid.UUID directly from _serialize — do NOT wrap in uuid.UUID()
    token_str = token_repo.create_for_user(user_id)

    self._email_sender.send(
        to=email,
        subject="Password reset request",
        body=(
            f"You requested a password reset.\n\n"
            f"Your reset token: {token_str}\n\n"
            f"This token expires in 15 minutes.\n"
            f"If you did not request this, ignore this message."
        ),
    )

    return {
        "message": "If that email is registered, a reset email has been sent",
        "expires_in": 900,
    }
```

- [ ] **Step 4: Run the new test**

```
pytest tests/test_auth_gaps.py::test_forgot_password_response_has_message_not_token -v
```
Expected: PASS

- [ ] **Step 5: Update the existing forgot-password response test**

In `tests/test_auth_gaps.py`, find the test that checks the response body of `forgot-password` (it currently asserts `"token"` is in the body). Update it:

```python
def test_forgot_password_returns_message(auth_client):
    client, repo = auth_client
    _seed_user(repo, "dave")
    resp = client.post("/v1/auth/forgot-password", json={"email": "dave@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["expires_in"] == 900
    assert "message" in body
```

If the original test was named differently, update the assertion inside it rather than renaming.

- [ ] **Step 6: Run the full auth gaps test suite**

```
pytest tests/test_auth_gaps.py -v
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```
git add lib/services/user_service.py tests/test_auth_gaps.py
git commit -m "feat: inject IEmailSender into UserService; token removed from forgot-password response"
```

---

## Task 5: Wire Sender in `main.py` + Smoke Tests

**Files:**
- Modify: `main.py`
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Add sender imports and instantiation to `main.py`**

Add imports near the top with the other lib imports:

```python
from lib.email.console_sender import ConsoleSender
from lib.email.smtp_sender import SmtpSender
```

Inside `main()`, before the `UserService` instantiation, add:

```python
email_sender = SmtpSender(config) if config.email_sender == "smtp" else ConsoleSender()
```

- [ ] **Step 2: Pass `email_sender` wherever `UserService` is constructed in `main.py`**

There are two places `UserService` is constructed in `main.py`:

1. Inside `_make_backend`:
```python
def _make_backend(factory):
    return ServiceBackendAdapter(
        factory=factory,
        user_service=UserService(factory, email_sender=email_sender),
        scheduler=scheduler,
    )
```

2. Any other direct `UserService(factory)` call — update them all to `UserService(factory, email_sender=email_sender)`.

- [ ] **Step 3: Add module imports to smoke test**

In `tests/test_smoke.py`, add to the `module_path` parametrize list:

```python
"lib.email.console_sender",
"lib.email.smtp_sender",
```

- [ ] **Step 4: Run the full test suite**

```
pytest tests/ -q
```
Expected: all tests pass with no regressions.

- [ ] **Step 5: Commit**

```
git add main.py tests/test_smoke.py
git commit -m "feat: wire email_sender into main.py; ConsoleSender default, SmtpSender on config"
```
