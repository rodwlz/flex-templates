"""
ConnectionTester: test database connectivity with latency measurement.

Actions:
    - test: returns {"alive": bool, "latency_ms": float | None, "error": str | None}
"""
import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from lib.services.connection_tester import ConnectionTester
from lib.contracts.base import ActionResult


@pytest.fixture
def db_factory_working(db_factory):
    """A working SessionFactory (from conftest: in-memory SQLite)."""
    return db_factory


@pytest.fixture
def db_factory_broken():
    """A SessionFactory that fails on session() calls."""
    factory = Mock()
    factory.session.side_effect = SQLAlchemyError("Connection refused")
    return factory


class TestConnectionTester:
    """ConnectionTester service tests."""

    def test_test_returns_alive_true_on_working_connection(self, db_factory_working):
        """ConnectionTester.test() returns alive=True for working DB."""
        service = ConnectionTester(db_factory_working)
        result = service.test({})

        assert result["alive"] is True
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0
        assert result["error"] is None

    def test_test_handles_connection_failure(self, db_factory_broken):
        """Graceful error on connection failure, alive=False."""
        service = ConnectionTester(db_factory_broken)
        result = service.test({})

        assert result["alive"] is False
        assert result["latency_ms"] is None
        assert isinstance(result["error"], str)
        assert len(result["error"]) > 0

    def test_test_never_raises_exception(self, db_factory_broken):
        """Even with broken factory, always returns dict (not exception)."""
        service = ConnectionTester(db_factory_broken)

        # This should NOT raise; it should return a dict.
        result = service.test({})

        # Verify it's a dict (method returns dict, SimpleService wraps as ActionResult)
        assert isinstance(result, dict)
        assert "alive" in result
        assert "latency_ms" in result
        assert "error" in result

    def test_test_via_execute_wraps_result_as_action_result(self, db_factory_working):
        """SimpleService.execute wraps dict result as ActionResult."""
        from lib.contracts.base import ActionRequest

        service = ConnectionTester(db_factory_working)
        req = ActionRequest(action="test", data={})
        result = service.execute(req)

        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.data["alive"] is True
        assert result.error is None

    def test_test_latency_is_reasonable(self, db_factory_working):
        """Latency should be a small positive number (in-memory SQLite)."""
        service = ConnectionTester(db_factory_working)
        result = service.test({})

        assert result["latency_ms"] < 1000  # Should be < 1 second for in-memory DB
        assert result["latency_ms"] >= 0
