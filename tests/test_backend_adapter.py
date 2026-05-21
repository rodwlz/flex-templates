"""Unit tests for ServiceBackendAdapter (coordinator)."""
import uuid
import pytest

from lib.adapters.backend_adapter import ServiceBackendAdapter
from lib.services.user_service import UserService
from lib.tasks.scheduler import TaskScheduler


@pytest.fixture
def adapter(db_factory):
    user_service = UserService(db_factory)
    scheduler = TaskScheduler()
    return ServiceBackendAdapter(db_factory, user_service, scheduler)


@pytest.fixture
def adapter_with_user(adapter):
    adapter.users.create({"username": "alice", "email": "alice@test.com", "password": "secret"})
    return adapter


def test_login_stores_session(adapter_with_user):
    result = adapter_with_user.auth.login("alice", "secret")
    assert result["user"]["username"] == "alice"
    assert adapter_with_user.auth.current_user()["username"] == "alice"


def test_logout_clears_session(adapter_with_user):
    adapter_with_user.auth.login("alice", "secret")
    adapter_with_user.auth.logout()
    assert adapter_with_user.auth.current_user() is None


def test_current_user_none_before_login(adapter):
    assert adapter.auth.current_user() is None


def test_login_raises_on_bad_credentials(adapter_with_user):
    with pytest.raises(ValueError):
        adapter_with_user.auth.login("alice", "wrong")


def test_list_users_returns_paginate_shape(adapter_with_user):
    result = adapter_with_user.users.list(page=1, page_size=10)
    assert "items" in result
    assert "total" in result
    assert "pages" in result
    assert result["page"] == 1
    assert result["total"] >= 1


def test_create_user_returns_dict_with_id(adapter):
    user = adapter.users.create({"username": "bob", "email": "bob@test.com", "password": "pw"})
    assert user["username"] == "bob"
    assert "id" in user


def test_delete_user_returns_true(adapter):
    user = adapter.users.create({"username": "carol", "email": "carol@test.com", "password": "pw"})
    assert adapter.users.delete(user["id"]) is True


def test_delete_nonexistent_user_returns_false(adapter):
    assert adapter.users.delete(str(uuid.uuid4())) is False


def test_list_roles_empty_initially(adapter):
    assert adapter.roles.list() == []


def test_create_role_returns_dict(adapter):
    role = adapter.roles.create("admin")
    assert role["name"] == "admin"
    assert "id" in role


def test_delete_role_returns_true(adapter):
    role = adapter.roles.create("mod")
    assert adapter.roles.delete(role["id"]) is True


def test_list_roles_after_create(adapter):
    adapter.roles.create("viewer")
    roles = adapter.roles.list()
    assert any(r["name"] == "viewer" for r in roles)


def test_assign_and_remove_role(adapter):
    user = adapter.users.create({"username": "dave", "email": "dave@t.com", "password": "pw"})
    role = adapter.roles.create("editor")
    assert adapter.roles.assign(user["id"], role["id"]) is True
    assert adapter.roles.remove(user["id"], role["id"]) is True


def test_list_jobs_empty_without_scheduled_jobs(adapter):
    assert adapter.scheduler.list() == []


def test_list_jobs_returns_registered_job(adapter, db_factory):
    scheduler = TaskScheduler()
    svc = UserService(db_factory)
    a2 = ServiceBackendAdapter(db_factory, svc, scheduler)
    scheduler.add_job(lambda: None, "interval", seconds=3600, id="test-job", name="test job")
    scheduler.start()
    jobs = a2.scheduler.list()
    assert any(j["id"] == "test-job" for j in jobs)
    scheduler.stop()
