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
from lib.repositories.password_reset_token_repository import PasswordResetTokenRepository
from lib.repositories.user_repository import UserRepository
from lib.security.password import hash_password
from tests.conftest import _v1_app


class _CaptureSender:
    """Test double that records the last sent email body so tests can extract the token."""

    def __init__(self):
        self.last_body = ""

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.last_body = body

    def extract_token(self) -> str:
        """Parse raw token from the email body line 'Your reset token: <token>'."""
        for line in self.last_body.splitlines():
            if line.startswith("Your reset token:"):
                return line.split(":", 1)[1].strip()
        raise ValueError("No token found in captured email body")


@pytest.fixture
def auth_client(http_factory):
    app = _v1_app(auth_routes.router)
    return TestClient(app), UserRepository(http_factory)


@pytest.fixture
def auth_client_capture(http_factory):
    """auth_client variant with a CaptureSender injected — gives tests access to the reset token."""
    from lib.services.user_service import UserService
    sender = _CaptureSender()

    def _get_service_with_capture():
        return UserService(http_factory, email_sender=sender)

    app = _v1_app(auth_routes.router)
    app.dependency_overrides[auth_routes._get_service] = _get_service_with_capture
    return TestClient(app), UserRepository(http_factory), sender


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

def test_forgot_password_returns_message(auth_client):
    client, repo = auth_client
    _seed_user(repo)
    resp = client.post("/v1/auth/forgot-password",
                       json={"email": "alice@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["expires_in"] == 900
    assert "message" in body


def test_forgot_password_unknown_email_200_generic(auth_client):
    client, _ = auth_client
    resp = client.post("/v1/auth/forgot-password",
                       json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_forgot_password_response_has_message_not_token(auth_client):
    """Token must NOT appear in the response body after email sender is injected."""
    client, repo = auth_client
    _seed_user(repo, "charlie")
    resp = client.post("/v1/auth/forgot-password", json={"email": "charlie@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" not in body
    assert "message" in body
    assert "expires_in" in body


def test_reset_password_success(auth_client_capture):
    client, repo, sender = auth_client_capture
    _seed_user(repo)

    client.post("/v1/auth/forgot-password", json={"email": "alice@example.com"})
    token = sender.extract_token()

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


def test_reset_password_used_token_400(auth_client_capture):
    client, repo, sender = auth_client_capture
    _seed_user(repo)

    client.post("/v1/auth/forgot-password", json={"email": "alice@example.com"})
    token = sender.extract_token()
    client.post("/v1/auth/reset-password",
                json={"token": token, "new_password": "pass2"})
    resp = client.post("/v1/auth/reset-password",
                       json={"token": token, "new_password": "pass3"})
    assert resp.status_code == 400
