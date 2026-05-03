"""HTTP API tests for cache routes."""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.api.routes import caches as caches_routes
from lib.contracts.base import ActionResult
from lib.services.cache_registry import CacheRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    saved = dict(CacheRegistry._adapters)
    CacheRegistry._adapters = {}
    yield
    CacheRegistry._adapters = saved


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(caches_routes.router)
    return TestClient(app)


# ── /caches/ ───────────────────────────────────────────────────────────────

def test_list_caches_empty(client):
    response = client.get("/caches/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_caches_returns_sorted_names(client):
    CacheRegistry.register("zeta", MagicMock())
    CacheRegistry.register("alpha", MagicMock())

    response = client.get("/caches/")
    assert response.status_code == 200
    assert response.json() == ["alpha", "zeta"]


# ── /caches/{name} ─────────────────────────────────────────────────────────

def test_get_cache_status_alive(client):
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"keys": ["a", "b"]}
    )
    CacheRegistry.register("redis", adapter)

    response = client.get("/caches/redis")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["alive"] is True
    assert body["data"]["info"] == "2 keys"


def test_get_cache_status_404_when_missing(client):
    response = client.get("/caches/nonexistent")
    assert response.status_code == 404
    assert "not registered" in response.json()["detail"]


# ── /caches/{name}/{action} ────────────────────────────────────────────────

def test_invoke_action_forwards_to_adapter(client):
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"key": "foo", "value": "bar", "found": True}
    )
    CacheRegistry.register("redis", adapter)

    response = client.post("/caches/redis/get", json={"key": "foo"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["value"] == "bar"

    # Verify the adapter saw the right ActionRequest.
    request_arg = adapter.execute.call_args[0][0]
    assert request_arg.action == "get"
    assert request_arg.data == {"key": "foo"}


def test_invoke_action_returns_failure_from_adapter(client):
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=False, error="key not found"
    )
    CacheRegistry.register("redis", adapter)

    response = client.post("/caches/redis/get", json={"key": "missing"})

    assert response.status_code == 200  # ActionResult, not HTTP failure
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "key not found"


def test_invoke_action_404_when_cache_missing(client):
    response = client.post("/caches/nope/get", json={"key": "x"})
    assert response.status_code == 404


def test_invoke_action_rejects_underscore_action(client):
    CacheRegistry.register("redis", MagicMock())
    response = client.post("/caches/redis/_private", json={})
    assert response.status_code == 400


def test_invoke_action_works_with_empty_body(client):
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"keys": []}
    )
    CacheRegistry.register("redis", adapter)

    response = client.post("/caches/redis/keys")

    assert response.status_code == 200
    assert response.json()["success"] is True
