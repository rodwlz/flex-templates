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
