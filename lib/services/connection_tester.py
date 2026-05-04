import time
from sqlalchemy import text
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory


class ConnectionTester(SimpleService):
    """
    Actions: test

    test(data: {}) -> {alive, latency_ms, error}
    """

    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def test(self, data: dict) -> dict:
        try:
            start = time.time()
            with self._factory.session() as s:
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
