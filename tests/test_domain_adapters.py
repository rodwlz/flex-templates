"""Domain adapter unit tests — each adapter tested in isolation."""
import uuid
import pytest

from lib.adapters.auth_adapter import ServiceAuthAdapter
from lib.adapters.users_adapter import ServiceUserAdapter
from lib.adapters.roles_adapter import ServiceRoleAdapter
from lib.adapters.scheduler_adapter import ServiceSchedulerAdapter
from lib.adapters.backend_adapter import ServiceBackendAdapter
from lib.services.user_service import UserService
from lib.tasks.scheduler import TaskScheduler


@pytest.fixture
def user_service(db_factory):
    return UserService(db_factory)

@pytest.fixture
def auth_adapter(user_service):
    return ServiceAuthAdapter(user_service)

@pytest.fixture
def users_adapter(db_factory, user_service):
    return ServiceUserAdapter(db_factory, user_service)

@pytest.fixture
def roles_adapter(db_factory):
    return ServiceRoleAdapter(db_factory)

@pytest.fixture
def scheduler_adapter():
    return ServiceSchedulerAdapter(None)

@pytest.fixture
def adapter(db_factory, user_service):
    scheduler = TaskScheduler()
    return ServiceBackendAdapter(db_factory, user_service, scheduler)

@pytest.fixture
def user_service_with_alice(user_service):
    user_service.create_user("alice", "alice@test.com", "secret")
    return user_service


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_auth_login_stores_session(user_service_with_alice, auth_adapter):
    result = auth_adapter.login("alice", "secret")
    assert result["user"]["username"] == "alice"
    assert auth_adapter.current_user()["username"] == "alice"

def test_auth_login_response_has_no_password_hash(user_service_with_alice, auth_adapter):
    result = auth_adapter.login("alice", "secret")
    assert "password_hash" not in result["user"]
    assert "salt" not in result["user"]

def test_auth_current_user_none_on_fresh_adapter(auth_adapter):
    assert auth_adapter.current_user() is None

def test_auth_logout_clears_session(user_service_with_alice, auth_adapter):
    auth_adapter.login("alice", "secret")
    auth_adapter.logout()
    assert auth_adapter.current_user() is None

def test_auth_login_failure_leaks_no_user_data(user_service_with_alice, auth_adapter):
    with pytest.raises(ValueError):
        auth_adapter.login("alice", "wrong_password")
    assert auth_adapter.current_user() is None


# ── Users ─────────────────────────────────────────────────────────────────────

def test_users_list_returns_paginate_shape(users_adapter, user_service):
    user_service.create_user("bob", "bob@test.com", "pw")
    result = users_adapter.list(page=1, page_size=10)
    assert "items" in result
    assert "total" in result
    assert "pages" in result
    assert result["page"] == 1

def test_users_list_items_have_no_password_hash(users_adapter, user_service):
    user_service.create_user("carol", "carol@test.com", "pw")
    items = users_adapter.list()["items"]
    for item in items:
        assert "password_hash" not in item
        assert "salt" not in item

def test_users_create_returns_dict_with_id(users_adapter):
    user = users_adapter.create({"username": "dave", "email": "dave@test.com", "password": "pw"})
    assert user["username"] == "dave"
    assert "id" in user

def test_users_create_response_has_no_password_hash(users_adapter):
    user = users_adapter.create({"username": "eve", "email": "eve@test.com", "password": "pw"})
    assert "password_hash" not in user
    assert "salt" not in user

def test_users_delete_returns_true(users_adapter):
    user = users_adapter.create({"username": "frank", "email": "frank@test.com", "password": "pw"})
    assert users_adapter.delete(user["id"]) is True

def test_users_delete_nonexistent_returns_false(users_adapter):
    assert users_adapter.delete(str(uuid.uuid4())) is False


# ── Roles ─────────────────────────────────────────────────────────────────────

def test_roles_list_empty_initially(roles_adapter):
    assert roles_adapter.list() == []

def test_roles_create_returns_dict(roles_adapter):
    role = roles_adapter.create("admin")
    assert role["name"] == "admin"
    assert "id" in role

def test_roles_delete_returns_true(roles_adapter):
    role = roles_adapter.create("mod")
    assert roles_adapter.delete(role["id"]) is True

def test_roles_assign_and_remove(users_adapter, roles_adapter):
    user = users_adapter.create({"username": "grace", "email": "grace@test.com", "password": "pw"})
    role = roles_adapter.create("editor")
    assert roles_adapter.assign(user["id"], role["id"]) is True
    assert roles_adapter.remove(user["id"], role["id"]) is True

def test_roles_assign_nonexistent_user_returns_false(roles_adapter):
    role = roles_adapter.create("viewer")
    assert roles_adapter.assign(str(uuid.uuid4()), role["id"]) is False

def test_roles_assign_nonexistent_role_returns_false(roles_adapter, users_adapter):
    user = users_adapter.create({"username": "harry", "email": "harry@test.com", "password": "pw"})
    assert roles_adapter.assign(user["id"], str(uuid.uuid4())) is False

def test_roles_delete_nonexistent_returns_false(roles_adapter):
    assert roles_adapter.delete(str(uuid.uuid4())) is False

def test_roles_remove_role_not_assigned_returns_false(roles_adapter, users_adapter):
    user = users_adapter.create({"username": "ivy", "email": "ivy@test.com", "password": "pw"})
    role = roles_adapter.create("superuser")
    assert roles_adapter.remove(user["id"], role["id"]) is False


# ── Scheduler ─────────────────────────────────────────────────────────────────

def test_scheduler_list_empty_without_scheduler(scheduler_adapter):
    assert scheduler_adapter.list() == []

def test_scheduler_list_returns_registered_job(db_factory, user_service):
    scheduler = TaskScheduler()
    adapter = ServiceBackendAdapter(db_factory, user_service, scheduler)
    scheduler.add_job(lambda: None, "interval", seconds=3600, id="test-job", name="test job")
    scheduler.start()
    jobs = adapter.scheduler.list()
    assert any(j["id"] == "test-job" for j in jobs)
    scheduler.stop()
