import uuid
from datetime import datetime, timezone, timedelta

import pytest

from lib.models.password_reset_token import PasswordResetToken
from lib.repositories.user_repository import UserRepository
from lib.repositories.password_reset_token_repository import PasswordResetTokenRepository
from lib.services.user_service import UserService
from lib.contracts.base import ActionRequest


@pytest.fixture
def svc(db_factory):
    return UserService(db_factory)


@pytest.fixture
def repo(db_factory):
    return UserRepository(db_factory)


def test_register_creates_user(svc, repo):
    result = svc.execute(ActionRequest(action="register", data={
        "username": "alice",
        "email": "alice@example.com",
        "password": "secret",
    }))
    assert result.success
    assert result.data["username"] == "alice"


def test_register_duplicate_username_fails(svc):
    svc.execute(ActionRequest(action="register", data={
        "username": "alice", "email": "a@example.com", "password": "x",
    }))
    result = svc.execute(ActionRequest(action="register", data={
        "username": "alice", "email": "b@example.com", "password": "x",
    }))
    assert not result.success
    assert "username" in result.error.lower()


def test_register_duplicate_email_fails(svc):
    svc.execute(ActionRequest(action="register", data={
        "username": "alice", "email": "shared@example.com", "password": "x",
    }))
    result = svc.execute(ActionRequest(action="register", data={
        "username": "bob", "email": "shared@example.com", "password": "x",
    }))
    assert not result.success
    assert "email" in result.error.lower()


def test_request_reset_returns_token(svc, repo):
    from lib.security.password import hash_password
    pw_hash, salt = hash_password("secret")
    repo.create({"username": "alice", "email": "alice@example.com",
                 "password_hash": pw_hash, "salt": salt})

    result = svc.execute(ActionRequest(action="request_reset",
                                       data={"email": "alice@example.com"}))
    assert result.success
    assert "token" in result.data
    assert result.data["expires_in"] == 900


def test_request_reset_unknown_email_returns_generic(svc):
    result = svc.execute(ActionRequest(action="request_reset",
                                       data={"email": "nobody@example.com"}))
    assert result.success
    assert "message" in result.data


def test_reset_password_changes_password(svc, repo, db_factory):
    from lib.security.password import hash_password, verify_password
    pw_hash, salt = hash_password("oldpass")
    repo.create({"username": "alice", "email": "alice@example.com",
                 "password_hash": pw_hash, "salt": salt})

    reset_result = svc.execute(ActionRequest(action="request_reset",
                                             data={"email": "alice@example.com"}))
    token = reset_result.data["token"]

    result = svc.execute(ActionRequest(action="reset_password",
                                       data={"token": token, "new_password": "newpass"}))
    assert result.success

    user = repo.find_for_auth("alice")
    assert verify_password("newpass", user["password_hash"])


def test_reset_password_invalid_token_fails(svc):
    result = svc.execute(ActionRequest(action="reset_password",
                                       data={"token": "a" * 64, "new_password": "x"}))
    assert not result.success
    assert "invalid" in result.error.lower()


def test_reset_password_used_token_fails(svc, repo, db_factory):
    from lib.security.password import hash_password
    pw_hash, salt = hash_password("pass")
    repo.create({"username": "alice", "email": "alice@example.com",
                 "password_hash": pw_hash, "salt": salt})

    reset_result = svc.execute(ActionRequest(action="request_reset",
                                             data={"email": "alice@example.com"}))
    token = reset_result.data["token"]

    # Use it once
    svc.execute(ActionRequest(action="reset_password",
                              data={"token": token, "new_password": "pass2"}))
    # Use it again — must fail
    result = svc.execute(ActionRequest(action="reset_password",
                                       data={"token": token, "new_password": "pass3"}))
    assert not result.success
