"""CacheTester — liveness + latency probe for any cache adapter.

Sends a `keys *` action to the adapter to verify the service is reachable
and that auth/permissions are working. Never raises — returns a dict that
SimpleService wraps as ActionResult.
"""
import time

from lib.contracts.base import ActionRequest
from lib.core.interfaces import SimpleService


class CacheTester(SimpleService):
    """Ping a cache adapter and report alive status, latency, key count.

    Actions:
        test → {alive, latency_ms, info, error}
            alive       — bool
            latency_ms  — float on success, None on failure
            info        — short status string ("N keys"), None on failure
            error       — message on failure, None on success
    """

    def __init__(self, adapter: SimpleService):
        self._adapter = adapter

    def test(self, data: dict) -> dict:
        try:
            start = time.time()
            result = self._adapter.execute(
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
