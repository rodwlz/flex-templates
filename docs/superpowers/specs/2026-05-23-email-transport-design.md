# Email Transport — Design Spec

**Date:** 2026-05-23

## Goal

Make the password-reset email pluggable so the framework works out of the box in dev
(token printed to console) and swaps to real email in one line when a mail server is
available (self-hosted Mailcow/Postfix on Proxmox, or any SMTP provider).

## Design Principles

- Zero external dependencies for the dev default
- One-line swap in `main.py` to go to production email
- `UserService` never knows which sender is active — receives `IEmailSender` via constructor
- Token is removed from the HTTP response body; dev workflow uses console output instead

## Interface

Added to `lib/core/interfaces.py`:

```python
class IEmailSender(ABC):
    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> None: ...
```

Keyword-only arguments prevent positional confusion between `to`, `subject`, `body`.

## Implementations

### `lib/email/__init__.py`

Empty.

### `lib/email/console_sender.py` — dev default

```python
class ConsoleSender(IEmailSender):
    def send(self, *, to: str, subject: str, body: str) -> None:
        print(f"\n[EMAIL] To: {to}\n[EMAIL] Subject: {subject}\n[EMAIL] Body:\n{body}\n")
```

Zero dependencies. Always works. Token is visible in the terminal for manual testing.

### `lib/email/smtp_sender.py` — production

```python
class SmtpSender(IEmailSender):
    def __init__(self, config: AppConfig):
        self._host     = config.smtp_host
        self._port     = config.smtp_port
        self._username = config.smtp_username
        self._password = config.smtp_password
        self._from     = config.smtp_from

    def send(self, *, to: str, subject: str, body: str) -> None:
        # Uses smtplib — zero extra dependencies
        # STARTTLS on port 587, SSL on port 465
        ...
```

Uses Python's built-in `smtplib` — no third-party package needed.

## AppConfig Changes

Four new fields added to `lib/config/settings.py` (all read from `.secrets/.env`):

```python
email_sender:   str = "console"              # "console" | "smtp"
smtp_host:      str = ""
smtp_port:      int = 587
smtp_username:  str = ""
smtp_password:  str = ""                     # set in vault for prod
smtp_from:      str = "noreply@example.com"
```

## UserService Changes

### Constructor

```python
def __init__(self, factory: SessionFactory, email_sender: IEmailSender | None = None):
    super().__init__(factory)
    self._email_sender = email_sender or ConsoleSender()
```

`None` default means existing tests and usages that don't pass a sender continue to work
(they get `ConsoleSender`). No breaking change.

### `request_reset`

```python
def request_reset(self, data: dict) -> dict:
    ...
    token_str = token_repo.create_for_user(user_id)
    self._email_sender.send(
        to=email,
        subject="Password reset request",
        body=f"Your reset token: {token_str}\nExpires in 15 minutes.",
    )
    return {"message": "If that email is registered, a reset email has been sent", "expires_in": 900}
```

Token is no longer in the response body. `ConsoleSender` prints it to stdout for dev use.
The generic "if that email is registered" message is preserved — no email enumeration.

## Wiring in `main.py`

```python
from lib.email.console_sender import ConsoleSender
from lib.email.smtp_sender import SmtpSender

email_sender = SmtpSender(config) if config.email_sender == "smtp" else ConsoleSender()
user_service = UserService(ConnectionRegistry.get(), email_sender=email_sender)
```

Adding a third provider (Resend, Mailgun, Postfix on Proxmox) = one new class + one new
`elif` branch. Nothing else changes.

## Test Impact

`tests/test_auth_gaps.py` — `POST /v1/auth/forgot-password` response shape changes:
- Before: `{"token": "...", "expires_in": 900}`
- After:  `{"message": "...", "expires_in": 900}`

Update the assertion. No other test changes needed — `UserService` defaults to
`ConsoleSender` so all existing service tests work without modification.

New `tests/test_email_senders.py`:
- `ConsoleSender` — assert `send()` prints the expected lines to stdout (use `capsys`)
- `SmtpSender` — patch `smtplib.SMTP` and assert `sendmail` is called with correct args

## Files Created / Modified

| File | Action |
|---|---|
| `lib/core/interfaces.py` | Modify — add `IEmailSender` ABC |
| `lib/email/__init__.py` | Create — empty |
| `lib/email/console_sender.py` | Create |
| `lib/email/smtp_sender.py` | Create |
| `lib/config/settings.py` | Modify — add email/smtp fields |
| `lib/services/user_service.py` | Modify — inject `IEmailSender`, update `request_reset` |
| `main.py` | Modify — instantiate sender, pass to UserService |
| `tests/test_email_senders.py` | Create |
| `tests/test_auth_gaps.py` | Modify — update forgot-password response assertion |
| `tests/test_smoke.py` | Modify — add `lib.email.console_sender`, `lib.email.smtp_sender` |
