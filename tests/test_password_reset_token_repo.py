import uuid
from datetime import datetime, timezone, timedelta

import pytest

from lib.models.password_reset_token import PasswordResetToken
from lib.repositories.password_reset_token_repository import PasswordResetTokenRepository
from lib.repositories.user_repository import UserRepository


@pytest.fixture
def token_repo(db_factory):
    return PasswordResetTokenRepository(db_factory)


@pytest.fixture
def user_id(db_factory):
    repo = UserRepository(db_factory)
    user = repo.create({
        "username": "alice",
        "email": "alice@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    return user.id


def test_create_for_user_returns_64_char_hex(token_repo, user_id):
    token_str = token_repo.create_for_user(user_id)
    assert len(token_str) == 64
    assert all(c in "0123456789abcdef" for c in token_str)


def test_find_valid_returns_dict_for_fresh_token(token_repo, user_id):
    token_str = token_repo.create_for_user(user_id)
    result = token_repo.find_valid(token_str)
    assert result is not None
    assert result["user_id"] == str(user_id)
    assert result["token"] == token_str


def test_find_valid_returns_none_for_unknown_token(token_repo):
    result = token_repo.find_valid("a" * 64)
    assert result is None


def test_mark_used_makes_token_invalid(token_repo, user_id):
    token_str = token_repo.create_for_user(user_id)
    row = token_repo.find_valid(token_str)
    token_repo.mark_used(uuid.UUID(row["id"]))
    assert token_repo.find_valid(token_str) is None


def test_find_valid_ignores_expired_token(token_repo, user_id, db_factory):
    """Manually insert a token with expires_at in the past."""
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    raw = "b" * 64
    with db_factory.session() as s:
        s.add(PasswordResetToken(
            user_id=user_id,
            token_hash=PasswordResetToken.hash_token(raw),
            expires_at=expired_at,
        ))
    assert token_repo.find_valid(raw) is None
