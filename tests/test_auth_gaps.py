"""
Integration tests for the three new public auth endpoints:
  POST /v1/auth/register
  POST /v1/auth/forgot-password
  POST /v1/auth/reset-password
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from lib.api.routes import auth as auth_routes
from lib.repositories.user_repository import UserRepository
from lib.security.password import hash_password
from tests.conftest import _v1_app


@pytest.fixture
def auth_client(http_factory):
    app = _v1_app(auth_routes.router)
    return TestClient(app), UserRepository(http_factory)


def _register(client, username="alice", email=None, password="secret"):
    return client.post("/v1/auth/register", json={
        "username": username,
        "email": email or f"{username}@example.com",
        "password": password,
    })


def _seed_user(repo, username="alice", password="secret"):
    pw_hash, salt = hash_password(password)
    repo.create({
        "username": username,
        "email": f"{username}@example.com",
        "password_hash": pw_hash,
        "salt": salt,
    })


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_returns_201(auth_client):
    client, _ = auth_client
    resp = _register(client)
    assert resp.status_code == 201


def test_register_response_has_user_fields(auth_client):
    client, _ = auth_client
    body = _register(client).json()
    assert "user_id" in body
    assert body["username"] == "alice"
    assert body["is_active"] is True


def test_register_duplicate_username_returns_409(auth_client):
    client, _ = auth_client
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409
    assert "username" in resp.json()["detail"].lower()


def test_register_duplicate_email_returns_409(auth_client):
    client, _ = auth_client
    _register(client, username="alice", email="shared@example.com")
    resp = _register(client, username="bob", email="shared@example.com")
    assert resp.status_code == 409
    assert "email" in resp.json()["detail"].lower()


# ── is_active login block ─────────────────────────────────────────────────────

def test_disabled_user_cannot_login(auth_client):
    client, repo = auth_client
    _seed_user(repo, username="dave")
    user = repo.find_for_auth("dave")
    repo.update(uuid.UUID(user["id"]), {"is_active": False})
    resp = client.post("/v1/auth/login",
                       data={"username": "dave", "password": "secret"})
    assert resp.status_code == 401


# ── Password reset ────────────────────────────────────────────────────────────

def test_forgot_password_returns_token(auth_client):
    client, repo = auth_client
    _seed_user(repo)
    resp = client.post("/v1/auth/forgot-password",
                       json={"email": "alice@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["expires_in"] == 900


def test_forgot_password_unknown_email_200_generic(auth_client):
    client, _ = auth_client
    resp = client.post("/v1/auth/forgot-password",
                       json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_reset_password_success(auth_client):
    client, repo = auth_client
    _seed_user(repo)

    token_resp = client.post("/v1/auth/forgot-password",
                             json={"email": "alice@example.com"})
    token = token_resp.json()["token"]

    resp = client.post("/v1/auth/reset-password",
                       json={"token": token, "new_password": "newpass123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    login_resp = client.post("/v1/auth/login",
                             data={"username": "alice", "password": "newpass123"})
    assert login_resp.status_code == 200


def test_reset_password_invalid_token_400(auth_client):
    client, _ = auth_client
    resp = client.post("/v1/auth/reset-password",
                       json={"token": "a" * 64, "new_password": "x"})
    assert resp.status_code == 400


def test_reset_password_used_token_400(auth_client):
    client, repo = auth_client
    _seed_user(repo)

    token = client.post("/v1/auth/forgot-password",
                        json={"email": "alice@example.com"}).json()["token"]
    client.post("/v1/auth/reset-password",
                json={"token": token, "new_password": "pass2"})
    resp = client.post("/v1/auth/reset-password",
                       json={"token": token, "new_password": "pass3"})
    assert resp.status_code == 400
