"""Integration tests for Http*Adapters against a real FastAPI test app."""
import pytest
from lib.auth.jwt_handler import create_token


def _inject_admin(http_backend) -> None:
    """Pre-load an admin JWT into the shared session — no DB user needed."""
    token = create_token({"sub": "00000000-0000-0000-0000-000000000001", "roles": ["admin"]})
    http_backend.auth._session.set_credentials(token, {"id": "00000000-0000-0000-0000-000000000001", "roles": ["admin"]})


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
    _inject_admin(http_backend)
    result = http_backend.users.create({
        "username": "newuser", "email": "new@x.com", "password": "pass",
    })
    assert "id" in result
    assert result["username"] == "newuser"


def test_http_users_delete_returns_true(http_backend, http_factory):
    from lib.services.user_service import UserService
    _inject_admin(http_backend)
    user = UserService(http_factory).create_user("todelete", "del@x.com", "pass")
    result = http_backend.users.delete(user["id"])
    assert result is True


def test_http_users_delete_nonexistent_returns_false(http_backend):
    import uuid
    result = http_backend.users.delete(str(uuid.uuid4()))
    assert result is False


# ── Roles ─────────────────────────────────────────────────────────────────────

def test_http_roles_list_empty(http_backend):
    result = http_backend.roles.list()
    assert result == []


def test_http_roles_create(http_backend):
    role = http_backend.roles.create("admin")
    assert "id" in role
    assert role["name"] == "admin"


def test_http_roles_delete(http_backend):
    role = http_backend.roles.create("viewer")
    result = http_backend.roles.delete(role["id"])
    assert result is True


def test_http_roles_assign(http_backend, test_user):
    role = http_backend.roles.create("editor")
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    result = http_backend.roles.assign(user["id"], role["id"])
    assert result is True


def test_http_roles_remove(http_backend, test_user):
    role = http_backend.roles.create("moderator")
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    http_backend.roles.assign(user["id"], role["id"])
    result = http_backend.roles.remove(user["id"], role["id"])
    assert result is True


# ── Scheduler ─────────────────────────────────────────────────────────────────

def test_http_scheduler_list_empty(http_backend):
    """Scheduler route returns [] when no scheduler is running."""
    result = http_backend.scheduler.list()
    assert result == []


# ── End-to-end: HttpBackendAdapter satisfies IBackendAdapter ──────────────────

def test_http_backend_adapter_end_to_end(http_backend, test_user, http_factory):
    """All four domains work in sequence through HttpBackendAdapter."""
    from lib.adapters.backend_adapter import IBackendAdapter
    assert isinstance(http_backend, IBackendAdapter)

    # auth
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    assert user["username"] == test_user["username"]

    # users
    listing = http_backend.users.list()
    assert listing["total"] >= 1

    # roles
    role = http_backend.roles.create("superuser")
    http_backend.roles.assign(user["id"], role["id"])
    http_backend.roles.remove(user["id"], role["id"])
    http_backend.roles.delete(role["id"])

    # scheduler
    jobs = http_backend.scheduler.list()
    assert isinstance(jobs, list)

    # logout
    http_backend.auth.logout()
    assert http_backend.auth.current_user() is None
