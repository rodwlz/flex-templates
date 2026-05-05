"""CacheTester — liveness + latency probe for any registered cache adapter."""
import time

from lib.contracts.base import ActionRequest
from lib.core.interfaces import SimpleService
from lib.services.cache_registry import CacheRegistry


class CacheTester(SimpleService):
    """
    Actions: test

    test(data: {name}) -> {alive, latency_ms, info, error}
        Looks up the named adapter in CacheRegistry, runs `keys *` to verify
        reachability + auth, and reports liveness, latency, and key count.
    """

    def test(self, data: dict) -> dict:
        try:
            adapter = CacheRegistry.get(data["name"])
            start = time.time()
            result = adapter.execute(
                ActionRequest(action="keys", data={"pattern": "*"})
            )
            latency_ms = (time.time() - start) * 1000

            if result.success:
                count = len(result.data.get("keys", []))
                return {
                    "alive": True,
                    "latency_ms": latency_ms,
                    "info": f"{count} keys",
                    "error": None,
                }
            return {
                "alive": False,
                "latency_ms": None,
                "info": None,
                "error": result.error or "ping failed",
            }
        except Exception as exc:
            return {
                "alive": False,
                "latency_ms": None,
                "info": None,
                "error": str(exc),
            }
