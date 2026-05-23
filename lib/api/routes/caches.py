"""
HTTP routes for cache adapters.

The view at /admin/caches drives caches through CacheRegistry — these endpoints
expose the same registry over HTTP so external clients can use it identically.

Routes:
    GET  /caches/                 → ["redis", "redis_main", ...]
    GET  /caches/{name}           → ActionResult{alive, latency_ms, info, error}
    POST /caches/{name}/{action}  → ActionResult — invokes any adapter action
                                    Body: the data dict (e.g. {"key": "x"})

The {action} segment maps directly to ActionRequest.action, so any new action
added to the underlying adapter (get/set/delete/keys/exists/expire/ttl/...)
becomes available over HTTP automatically.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from lib.contracts.base import ActionRequest
from lib.services.cache_registry import CacheRegistry
from lib.services.cache_tester import CacheTester


router = APIRouter(prefix="/caches", tags=["caches"])

_tester = CacheTester()


def _get_or_404(name: str):
    try:
        return CacheRegistry.get(name)
    except RuntimeError:
        raise HTTPException(404, f"Cache adapter {name!r} not registered")


@router.get("/")
def list_caches() -> list[str]:
    """Return every registered cache adapter name, sorted."""
    return sorted(CacheRegistry.list())


@router.get("/{name}")
def get_cache_status(name: str) -> dict:
    """Run CacheTester against the named adapter and return alive/latency/info."""
    _get_or_404(name)
    result = _tester.execute(ActionRequest(action="test", data={"name": name}))
    return result.model_dump()


@router.post("/{name}/{action}")
def invoke_action(name: str, action: str, data: dict = Body(default_factory=dict)) -> dict:
    """Forward {action} + body to the named adapter and return its ActionResult."""
    adapter = _get_or_404(name)
    if action.startswith("_"):
        raise HTTPException(400, "Action name cannot start with underscore")
    result = adapter.execute(ActionRequest(action=action, data=data))
    return result.model_dump()
