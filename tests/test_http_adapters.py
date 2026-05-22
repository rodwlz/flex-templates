"""Integration tests for Http*Adapters against a real FastAPI test app."""
import pytest


# ── Auth ─────────────────────────────────────────────────────────────────────

def test_http_login_returns_user_dict(http_backend, test_user):
    result = http_backend.auth.login(test_user["username"], test_user["password"])
    assert "user" in result
    assert result["user"]["username"] == test_user["username"]
    assert result["user"]["email"] == test_user["email"]
    assert "password_hash" not in result["user"]


def test_http_login_bad_credentials_raises(http_backend):
    with pytest.raises(ValueError):
        http_backend.auth.login("nobody", "wrongpass")


def test_http_current_user_none_before_login(http_backend):
    assert http_backend.auth.current_user() is None


def test_http_current_user_after_login(http_backend, test_user):
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    assert user is not None
    assert user["username"] == test_user["username"]


def test_http_current_user_uses_cache(http_backend, test_user):
    """Two consecutive calls return identical dicts (cache, not two /me requests)."""
    http_backend.auth.login(test_user["username"], test_user["password"])
    u1 = http_backend.auth.current_user()
    u2 = http_backend.auth.current_user()
    assert u1 == u2


def test_http_logout_clears_user(http_backend, test_user):
    http_backend.auth.login(test_user["username"], test_user["password"])
    http_backend.auth.logout()
    assert http_backend.auth.current_user() is None
