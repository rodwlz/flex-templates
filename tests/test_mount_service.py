"""
mount_service: turn any SimpleService into HTTP routes with one line.

Each public action method becomes POST /{prefix}/{action}, accepting JSON
that maps to ActionRequest.data, returning the ActionResult as JSON.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.api.mount_service import mount_service
from lib.contracts.base import ActionResult
from lib.core.interfaces import SimpleService


class _DemoService(SimpleService):
    """Tiny service used to prove the auto-router pattern."""

    def __init__(self):
        self.last_call = None

    def create(self, data: dict) -> dict:
        self.last_call = ("create", data)
        return {"created": data.get("name", "anon")}

    def get(self, data: dict) -> dict:
        self.last_call = ("get", data)
        return {"id": data.get("id"), "name": "alice"}

    def fail(self, data: dict) -> dict:
        raise ValueError("boom")


def _client(service, prefix="/demo"):
    app = FastAPI()
    app.include_router(mount_service(service, prefix=prefix))
    return TestClient(app)


def test_mount_service_generates_routes_for_each_action():
    """Every public method on the service becomes a POST endpoint."""
    service = _DemoService()
    app = FastAPI()
    app.include_router(mount_service(service, prefix="/demo"))

    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/demo/create" in paths
    assert "/demo/get" in paths
    assert "/demo/fail" in paths


def test_mount_service_calls_underlying_service_action():
    """POSTing to /create routes the body into ActionRequest.data."""
    service = _DemoService()
    client = _client(service)

    response = client.post("/demo/create", json={"name": "alice"})

    assert response.status_code == 200
    assert service.last_call == ("create", {"name": "alice"})


def test_mount_service_returns_action_result_as_json():
    """A successful action returns the full ActionResult dict (success + data)."""
    service = _DemoService()
    client = _client(service)

    payload = client.post("/demo/create", json={"name": "alice"}).json()

    assert payload["success"] is True
    assert payload["data"] == {"created": "alice"}
    assert payload["error"] is None


def test_mount_service_returns_failed_action_result_when_handler_raises():
    """SimpleService catches handler exceptions; mount_service surfaces them as JSON."""
    service = _DemoService()
    client = _client(service)

    payload = client.post("/demo/fail", json={}).json()

    assert payload["success"] is False
    assert "boom" in payload["error"]


def test_mount_service_skips_dispatcher_and_staging_methods():
    """`execute`, `stage`, `confirm`, `cancel` are framework hooks — never routed."""
    service = _DemoService()
    app = FastAPI()
    app.include_router(mount_service(service, prefix="/demo"))

    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/demo/execute" not in paths
    assert "/demo/stage" not in paths
    assert "/demo/confirm" not in paths
    assert "/demo/cancel" not in paths


def test_mount_service_handles_empty_body():
    """Routes work when called with no body (data defaults to empty dict)."""
    service = _DemoService()
    client = _client(service)

    payload = client.post("/demo/get", json={}).json()

    assert payload["success"] is True
    assert service.last_call == ("get", {})
