"""
Repository CRUD tests. Uses in-memory SQLite from conftest fixtures.
"""
import pytest
from lib.database.query import safe_query
from lib.models.user import User
from lib.repositories.role_repository import RoleRepository


def test_create_user(user_repo):
    user = user_repo.create({"username": "alice", "email": "alice@example.com",
                              "password_hash": "hash1", "salt": "salt1"})
    assert user.id is not None
    assert user.username == "alice"


def test_get_user(user_repo):
    user = user_repo.create({"username": "bob", "email": "bob@example.com",
                              "password_hash": "hash2", "salt": "salt2"})
    fetched = user_repo.get(user.id)
    assert fetched is not None
    assert fetched.username == "bob"


def test_get_nonexistent_user(user_repo):
    import uuid
    assert user_repo.get(uuid.uuid4()) is None


def test_list_users(user_repo):
    user_repo.create({"username": "charlie", "email": "c@example.com",
                      "password_hash": "hash3", "salt": "salt3", "status": "admin"})
    user_repo.create({"username": "diana", "email": "d@example.com",
                      "password_hash": "hash4", "salt": "salt4", "status": "base-user"})

    users = user_repo.list()
    assert len(users) == 2

    admins = user_repo.list(status="admin")
    assert len(admins) == 1
    assert admins[0].username == "charlie"


def test_update_user(user_repo):
    user = user_repo.create({"username": "eve", "email": "eve@example.com",
                              "password_hash": "hash5", "salt": "salt5"})
    updated = user_repo.update(user.id, {"status": "admin"})
    assert updated is not None
    assert updated.status == "admin"

    fetched = user_repo.get(user.id)
    assert fetched.status == "admin"


def test_update_nonexistent_user(user_repo):
    import uuid
    assert user_repo.update(uuid.uuid4(), {"status": "admin"}) is None


def test_delete_user(user_repo):
    user = user_repo.create({"username": "frank", "email": "f@example.com",
                              "password_hash": "hash6", "salt": "salt6"})
    assert user_repo.delete(user.id) is True
    assert user_repo.get(user.id) is None


def test_delete_nonexistent_user(user_repo):
    import uuid
    assert user_repo.delete(uuid.uuid4()) is False


def test_safe_query_returns_rows(db_factory):
    with db_factory.session() as s:
        s.add(User(username="grace", email="g@example.com",
                   password_hash="hash7", salt="salt7"))
        s.commit()

    with db_factory.session() as s:
        rows = safe_query(s, "SELECT username, email FROM users WHERE username = :name", name="grace")
        assert len(rows) == 1
        assert rows[0]["username"] == "grace"
        assert rows[0]["email"] == "g@example.com"


def test_safe_query_parameterized(db_factory):
    with db_factory.session() as s:
        s.add(User(username="henry", email="h@example.com",
                   password_hash="hash8", salt="salt8"))
        s.commit()

    with db_factory.session() as s:
        rows = safe_query(s, "SELECT * FROM users WHERE username = :u OR email = :e",
                          u="henry", e="h@example.com")
        assert len(rows) == 1


def test_role_repository_create(db_factory):
    repo = RoleRepository(db_factory)
    role = repo.create({"name": "admin", "description": "Admin role"})
    assert role.name == "admin"
    assert role.id is not None


def test_role_repository_get(db_factory):
    repo = RoleRepository(db_factory)
    role = repo.create({"name": "editor", "description": "Editor role"})
    retrieved = repo.get(role.id)
    assert retrieved.name == "editor"


def test_role_repository_list(db_factory):
    repo = RoleRepository(db_factory)
    repo.create({"name": "admin", "description": "Admin"})
    repo.create({"name": "editor", "description": "Editor"})
    roles = repo.list()
    assert len(roles) == 2
