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


# ── Users ─────────────────────────────────────────────────────────────────────

def test_http_users_list_returns_paginate_shape(http_backend, test_user):
    result = http_backend.users.list()
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result
    assert "pages" in result
    assert result["total"] >= 1


def test_http_users_list_page2_offset(http_backend, http_factory):
    """Page 2 with page_size=1 returns the second user."""
    from lib.services.user_service import UserService
    svc = UserService(http_factory)
    svc.create_user("user_a", "a@x.com", "pass")
    svc.create_user("user_b", "b@x.com", "pass")
    result = http_backend.users.list(page=2, page_size=1)
    assert result["page"] == 2
    assert len(result["items"]) == 1


def test_http_users_create_returns_dict_with_id(http_backend):
    result = http_backend.users.create({
        "username": "newuser", "email": "new@x.com", "password": "pass",
    })
    assert "id" in result
    assert result["username"] == "newuser"


def test_http_users_delete_returns_true(http_backend, http_factory):
    from lib.services.user_service import UserService
    user = UserService(http_factory).create_user("todelete", "del@x.com", "pass")
    result = http_backend.users.delete(user["id"])
    assert result is True


def test_http_users_delete_nonexistent_returns_false(http_backend):
    import uuid
    result = http_backend.users.delete(str(uuid.uuid4()))
    assert result is False
