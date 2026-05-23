import pytest
from lib.repositories.user_repository import UserRepository
from lib.services.user_service import UserService


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


def test_is_active_false_blocks_authenticate(db_factory, repo):
    """authenticate() raises ValueError when is_active=False (even with correct password)."""
    from lib.security.password import hash_password
    pw_hash, salt = hash_password("correctpass")
    user = repo.create({
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": pw_hash,
        "salt": salt,
    })
    # Disable the account
    repo.update(user.id, {"is_active": False})

    svc = UserService(db_factory)
    with pytest.raises(ValueError, match="disabled"):
        svc.authenticate({"username": "bob", "password": "correctpass"})


def test_is_active_true_allows_authenticate(db_factory, repo):
    """authenticate() returns user dict when is_active=True (default)."""
    from lib.security.password import hash_password
    pw_hash, salt = hash_password("secret")
    repo.create({
        "username": "carol",
        "email": "carol@example.com",
        "password_hash": pw_hash,
        "salt": salt,
    })
    svc = UserService(db_factory)
    result = svc.authenticate({"username": "carol", "password": "secret"})
    assert result["username"] == "carol"
