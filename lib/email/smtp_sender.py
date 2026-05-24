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
