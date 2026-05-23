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
