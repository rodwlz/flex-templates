---
title: "Email Transport"
category: guide
audience: [developer, agent]
related:
  - ../core/CONVENTIONS.md
  - ../core/ARCHITECTURE.md
agent_priority: low
---

# Email Transport

How to send email from services — configure the sender, swap implementations, inject into routes, and write tests without hitting a real server.

---

## Overview

Email transport follows the same pluggable pattern as every other framework component: one abstract interface, two built-in implementations, wired in `main.py`.

```
IEmailSender                   ← lib/core/interfaces.py
  ├── ConsoleSender             ← lib/email/console_sender.py  (dev default)
  └── SmtpSender                ← lib/email/smtp_sender.py     (production)
```

The active sender is chosen at startup from `AppConfig.email_sender` (`"console"` or `"smtp"`) and injected into every service and route module that needs to send mail. Views never touch the sender directly.

---

## Calling `send()` from a Service

Inject `IEmailSender` through the service constructor — never import `ConsoleSender` or `SmtpSender` inside a service. `UserService` shows the canonical pattern:

```python
class UserService(StagingService):
    def __init__(self, factory: SessionFactory, email_sender=None):
        super().__init__(factory)
        if email_sender is None:
            from lib.email.console_sender import ConsoleSender  # lazy dev fallback
            email_sender = ConsoleSender()
        self._email_sender = email_sender

    def request_reset(self, data: dict) -> dict:
        # ... look up user, generate token ...
        self._email_sender.send(
            to=user["email"],
            subject="Password Reset",
            body=f"Reset your password: {reset_url}",
        )
        return {"message": "Reset email sent", "expires_in": 900}
```

All three arguments to `send()` are **keyword-only** — calling `send(addr, subj, body)` is a `TypeError`. This prevents argument-order bugs.

---

## Configuration

Set these in `.secrets/.env` (never in the project root `.env`):

| Variable | Default | Purpose |
|---|---|---|
| `EMAIL_SENDER` | `console` | `"console"` (dev) or `"smtp"` (prod) |
| `SMTP_HOST` | `""` | Mail server hostname |
| `SMTP_PORT` | `587` | 587 = STARTTLS, 465 = implicit SSL |
| `SMTP_USERNAME` | `""` | Auth username |
| `SMTP_PASSWORD` | `""` | Auth password |
| `SMTP_FROM` | `noreply@example.com` | From address |

`SmtpSender` detects port 465 automatically and uses `SMTP_SSL`; all other ports use STARTTLS.

**Gmail example** (use an App Password, not your account password):

```
EMAIL_SENDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=abcd-efgh-ijkl-mnop
SMTP_FROM=you@gmail.com
```

---

## ConsoleSender — dev default

Prints the full email to stdout. Zero config, always available, safe in tests:

```
[EMAIL] To: alice@example.com
[EMAIL] Subject: Password Reset
[EMAIL] Body:
Reset your password at: http://localhost:8080/reset?token=abc123
```

---

## Route Injection Pattern

Route modules that build services with email use a module-level setter function — the same pattern as `set_scheduler()` in the scheduler routes:

```python
# lib/api/routes/auth.py
_email_sender = None

def set_email_sender(sender) -> None:
    global _email_sender
    _email_sender = sender

def _get_service() -> UserService:
    return UserService(ConnectionRegistry.get(), email_sender=_email_sender)
```

`main.py` calls `set_email_sender(email_sender)` once at startup. Any route module that needs email follows the same pattern.

---

## Adding a Custom Sender

Implement `IEmailSender` from `lib/core/interfaces.py`:

```python
from lib.core.interfaces import IEmailSender

class SendGridSender(IEmailSender):
    def __init__(self, api_key: str):
        self._api_key = api_key

    def send(self, *, to: str, subject: str, body: str) -> None:
        import httpx
        httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"personalizations": [{"to": [{"email": to}]}],
                  "from": {"email": "noreply@example.com"},
                  "subject": subject,
                  "content": [{"type": "text/plain", "value": body}]},
        )
```

Wire it in `main.py` (the only file that names concrete implementations):

```python
from lib.email.sendgrid_sender import SendGridSender

email_sender = SendGridSender(api_key=config.sendgrid_api_key)
```

No other files change.

---

## Testing with a Capture Sender

Inject a capture sender in tests to assert on email body without hitting a real server:

```python
class _CaptureSender:
    def __init__(self):
        self.sent: list[dict] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})

    def last_body(self) -> str:
        return self.sent[-1]["body"] if self.sent else ""


@pytest.fixture
def capture_svc(db_factory):
    sender = _CaptureSender()
    return UserService(db_factory, email_sender=sender), sender
```

Then assert on the captured email:

```python
def test_reset_email_contains_token(capture_svc):
    svc, sender = capture_svc
    svc.execute(ActionRequest(action="request_reset", data={"login": "admin@example.com"}))
    assert "token" in sender.last_body()
    assert sender.sent[-1]["to"] == "admin@example.com"
```

For API-level tests, override the FastAPI dependency:

```python
from lib.api.routes import auth as auth_routes

@pytest.fixture
def auth_client(app, monkeypatch):
    sender = _CaptureSender()
    monkeypatch.setattr(auth_routes, "_email_sender", sender)
    return TestClient(app), sender
```
