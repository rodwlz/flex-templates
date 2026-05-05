import time
from sqlalchemy import text
from lib.core.interfaces import SimpleService
from lib.database.session import ConnectionRegistry


class ConnectionTester(SimpleService):
    """
    Actions: test

    test(data: {name}) -> {alive, latency_ms, error}
        Looks up the named database in ConnectionRegistry, runs SELECT 1,
        and reports liveness + round-trip latency.
    """

    def test(self, data: dict) -> dict:
        try:
            factory = ConnectionRegistry.get(data["name"])
            start = time.time()
            with factory.session() as s:
                s.execute(text("SELECT 1"))
            return {
                "alive": True,
                "latency_ms": (time.time() - start) * 1000,
                "error": None,
            }
        except Exception as exc:
            return {
                "alive": False,
                "latency_ms": None,
                "error": str(exc),
            }
