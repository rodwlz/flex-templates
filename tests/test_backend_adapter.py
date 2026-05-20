"""Unit tests for ServiceBackendAdapter."""
import uuid
import pytest

from lib.adapters.backend_adapter import ServiceBackendAdapter
from lib.services.user_service import UserService
from lib.repositories.role_repository import RoleRepository
from lib.tasks.scheduler import TaskScheduler


@pytest.fixture
def adapter(db_factory):
    user_service = UserService(db_factory)
    role_repo = RoleRepository(db_factory)
    scheduler = TaskScheduler()
    return ServiceBackendAdapter(db_factory, user_service, role_repo, scheduler)


@pytest.fixture
def adapter_with_user(adapter):
    adapter.create_user({"username": "alice", "email": "alice@test.com", "password": "secret"})
    return adapter


def test_login_stores_session(adapter_with_user):
    result = adapter_with_user.login("alice", "secret")
    assert result["user"]["username"] == "alice"
    assert adapter_with_user.current_user()["username"] == "alice"


def test_logout_clears_session(adapter_with_user):
    adapter_with_user.login("alice", "secret")
    adapter_with_user.logout()
    assert adapter_with_user.current_user() is None


def test_current_user_none_before_login(adapter):
    assert adapter.current_user() is None


def test_login_raises_on_bad_credentials(adapter_with_user):
    with pytest.raises(ValueError):
        adapter_with_user.login("alice", "wrong")


def test_list_users_returns_paginate_shape(adapter_with_user):
    result = adapter_with_user.list_users(page=1, page_size=10)
    assert "items" in result
    assert "total" in result
    assert "pages" in result
    assert result["page"] == 1
    assert result["total"] >= 1


def test_create_user_returns_dict_with_id(adapter):
    user = adapter.create_user({"username": "bob", "email": "bob@test.com", "password": "pw"})
    assert user["username"] == "bob"
    assert "id" in user


def test_delete_user_returns_true(adapter):
    user = adapter.create_user({"username": "carol", "email": "carol@test.com", "password": "pw"})
    assert adapter.delete_user(user["id"]) is True


def test_delete_nonexistent_user_returns_false(adapter):
    assert adapter.delete_user(str(uuid.uuid4())) is False


def test_list_roles_empty_initially(adapter):
    assert adapter.list_roles() == []


def test_create_role_returns_dict(adapter):
    role = adapter.create_role("admin")
    assert role["name"] == "admin"
    assert "id" in role


def test_delete_role_returns_true(adapter):
    role = adapter.create_role("mod")
    assert adapter.delete_role(role["id"]) is True


def test_list_roles_after_create(adapter):
    adapter.create_role("viewer")
    roles = adapter.list_roles()
    assert any(r["name"] == "viewer" for r in roles)


def test_assign_and_remove_role(adapter):
    user = adapter.create_user({"username": "dave", "email": "dave@t.com", "password": "pw"})
    role = adapter.create_role("editor")
    assert adapter.assign_role(user["id"], role["id"]) is True
    assert adapter.remove_role(user["id"], role["id"]) is True


def test_list_jobs_empty_without_scheduled_jobs(adapter):
    assert adapter.list_jobs() == []


def test_list_jobs_returns_registered_job(adapter):
    scheduler = TaskScheduler()
    from lib.services.user_service import UserService
    from lib.repositories.role_repository import RoleRepository
    svc = UserService(adapter._factory)
    rr = RoleRepository(adapter._factory)
    a2 = ServiceBackendAdapter(adapter._factory, svc, rr, scheduler)
    scheduler.add_job(lambda: None, "interval", seconds=3600, id="test-job", name="test job")
    scheduler.start()
    jobs = a2.list_jobs()
    assert any(j["id"] == "test-job" for j in jobs)
    scheduler.stop()
