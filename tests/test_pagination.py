"""
Pagination tests for PaginatedResult and paginated GET /v1/users.

Tests the new pagination shape: items, total, page, page_size, pages.
"""
import pytest
from fastapi.testclient import TestClient

from lib.api.routes import users as users_routes
from lib.repositories.user_repository import UserRepository
from tests.conftest import _v1_app


@pytest.fixture
def paginate_client(http_factory):
    app = _v1_app(users_routes.router)
    return TestClient(app), UserRepository(http_factory)


def _make_user(repo, username):
    return repo.create({
        "username": username,
        "email": f"{username}@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })


def test_list_returns_pagination_metadata(paginate_client):
    """Response has items, total, page, page_size, pages keys."""
    client, repo = paginate_client
    _make_user(repo, "alice")
    _make_user(repo, "bob")

    resp = client.get("/v1/users?page=1&page_size=10")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("items", "total", "page", "page_size", "pages"):
        assert key in body, f"Missing key: {key}"


def test_list_correct_total(paginate_client):
    """total equals number of users created."""
    client, repo = paginate_client
    for name in ("alice", "bob", "carol", "dave", "eve"):
        _make_user(repo, name)

    body = client.get("/v1/users?page=1&page_size=20").json()
    assert body["total"] == 5


def test_list_page_2_returns_second_set(paginate_client):
    """page=2 returns a different set of items than page=1."""
    client, repo = paginate_client
    for name in ("alice", "bob", "carol"):
        _make_user(repo, name)

    page1 = client.get("/v1/users?page=1&page_size=2").json()
    page2 = client.get("/v1/users?page=2&page_size=2").json()

    names1 = {u["username"] for u in page1["items"]}
    names2 = {u["username"] for u in page2["items"]}
    assert len(names1) == 2
    assert len(names2) == 1
    assert names1.isdisjoint(names2)


def test_list_empty_db(paginate_client):
    """Empty database returns items=[], total=0, pages=0."""
    client, _ = paginate_client

    body = client.get("/v1/users?page=1&page_size=20").json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["pages"] == 0
