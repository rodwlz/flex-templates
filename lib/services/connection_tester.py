"""ConnectionTester: test database connectivity with latency measurement."""
import time
from sqlalchemy import text
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory


class ConnectionTester(SimpleService):
    """Service for testing database connectivity.

    Measures the time it takes to execute a simple query and returns
    alive status, latency, and any error message.

    Actions:
        - test: test database connectivity, returns {"alive": bool, "latency_ms": float | None, "error": str | None}
    """

    def __init__(self, factory: SessionFactory):
        """Initialize with a SessionFactory.

        Args:
            factory: SessionFactory instance
        """
        self._factory = factory

    def test(self, data: dict) -> dict:
        """Test database connectivity.

        Args:
            data: unused

        Returns:
            dict with keys:
                - alive: bool, True if connection successful
                - latency_ms: float | None, time in milliseconds for query (None on error)
                - error: str | None, error message if any
        """
        try:
            start = time.time()
            with self._factory.session() as s:
                s.execute(text("SELECT 1"))
            elapsed = time.time() - start
            latency_ms = elapsed * 1000

            return {
                "alive": True,
                "latency_ms": latency_ms,
                "error": None,
            }
        except Exception as exc:
            return {
                "alive": False,
                "latency_ms": None,
                "error": str(exc),
            }
