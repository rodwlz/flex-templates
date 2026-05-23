import pytest
from lib.repositories.user_repository import UserRepository


@pytest.fixture
def repo(db_factory):
    return UserRepository(db_factory)


def _make_user(repo, username="alice"):
    return repo.create({
        "username": username,
        "email": f"{username}@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })


def test_is_active_defaults_true(repo):
    user = _make_user(repo)
    assert user.is_active is True


def test_find_for_auth_includes_is_active(repo):
    _make_user(repo)
    result = repo.find_for_auth("alice")
    assert "is_active" in result
    assert result["is_active"] is True
