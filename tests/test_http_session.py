"""Unit tests for _HttpSession — HTTPS guard, token lifecycle, header injection."""
from unittest.mock import MagicMock, call

import httpx
import pytest

from lib.adapters.http_session import _HttpSession


def _mock_session() -> _HttpSession:
    """Return a session with a MagicMock client (no real network)."""
    return _HttpSession("http://ignored", _client=MagicMock(spec=httpx.Client))


# ── HTTPS guard ───────────────────────────────────────────────────────────────

def test_https_guard_rejects_remote_http():
    with pytest.raises(ValueError, match="HTTPS required"):
        _HttpSession("http://api.example.com")


def test_https_guard_allows_localhost_http():
    session = _HttpSession("http://localhost:8080")
    assert session.has_token() is False  # constructed successfully


def test_https_guard_allows_127_http():
    session = _HttpSession("http://127.0.0.1:8080")
    assert session.has_token() is False


def test_https_guard_allows_https_remote():
    session = _HttpSession("https://api.example.com")
    assert session.has_token() is False


# ── Token + user cache ────────────────────────────────────────────────────────

def test_no_auth_header_before_credentials_set():
    session = _mock_session()
    session.request("GET", "/test")
    _, kwargs = session._client.request.call_args
    assert "Authorization" not in kwargs.get("headers", {})


def test_auth_header_after_set_credentials():
    session = _mock_session()
    session.set_credentials("tok123", {"id": "u1"})
    session.request("GET", "/test")
    _, kwargs = session._client.request.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer tok123"


def test_clear_credentials_removes_token_and_user():
    session = _mock_session()
    session.set_credentials("tok123", {"id": "u1"})
    session.clear_credentials()
    assert session.has_token() is False
    assert session.get_cached_user() is None


def test_no_auth_header_after_clear():
    session = _mock_session()
    session.set_credentials("tok123", {"id": "u1"})
    session.clear_credentials()
    session.request("GET", "/test")
    _, kwargs = session._client.request.call_args
    assert "Authorization" not in kwargs.get("headers", {})


def test_get_cached_user_returns_none_initially():
    session = _mock_session()
    assert session.get_cached_user() is None


def test_get_cached_user_returns_stored_dict():
    session = _mock_session()
    session.set_credentials("tok", {"id": "u1", "username": "alice"})
    assert session.get_cached_user() == {"id": "u1", "username": "alice"}
