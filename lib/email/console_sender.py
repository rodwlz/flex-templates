from lib.core.interfaces import IEmailSender


class ConsoleSender(IEmailSender):
    """Dev email sender — prints message to stdout. Zero dependencies."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        print(f"\n[EMAIL] To: {to}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body:\n{body}\n")
