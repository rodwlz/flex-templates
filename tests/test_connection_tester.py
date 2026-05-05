"""
ConnectionTester: probe a registered database for liveness and latency.

Actions:
    - test(data: {name}) → {alive, latency_ms, error}
"""
from unittest.mock import Mock
import pytest
from sqlalchemy.exc import SQLAlchemyError

from lib.contracts.base import ActionRequest, ActionResult
from lib.database.session import ConnectionRegistry
from lib.services.connection_tester import ConnectionTester


@pytest.fixture(autouse=True)
def clean_registry():
    saved = dict(ConnectionRegistry._factories)
    ConnectionRegistry._factories = {}
    yield
    ConnectionRegistry._factories = saved


@pytest.fixture
def working_db(db_factory):
    """Register an in-memory SQLite factory under the name 'working'."""
    ConnectionRegistry._factories["working"] = db_factory
    return "working"


@pytest.fixture
def broken_db():
    """Register a factory whose session() raises."""
    factory = Mock()
    factory.session.side_effect = SQLAlchemyError("Connection refused")
    ConnectionRegistry._factories["broken"] = factory
    return "broken"


class TestConnectionTester:
    def test_returns_alive_true_on_working_connection(self, working_db):
        result = ConnectionTester().test({"name": working_db})

        assert result["alive"] is True
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0
        assert result["error"] is None

    def test_handles_connection_failure(self, broken_db):
        result = ConnectionTester().test({"name": broken_db})

        assert result["alive"] is False
        assert result["latency_ms"] is None
        assert "Connection refused" in result["error"]

    def test_never_raises_exception(self, broken_db):
        # Returns dict even when factory throws.
        result = ConnectionTester().test({"name": broken_db})
        assert isinstance(result, dict)
        assert set(result.keys()) == {"alive", "latency_ms", "error"}

    def test_unknown_name_returns_failure(self):
        result = ConnectionTester().test({"name": "does_not_exist"})
        assert result["alive"] is False
        assert result["error"] is not None

    def test_via_execute_wraps_result_as_action_result(self, working_db):
        tester = ConnectionTester()
        result = tester.execute(ActionRequest(action="test", data={"name": working_db}))

        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.data["alive"] is True
        assert result.error is None

    def test_latency_is_reasonable(self, working_db):
        result = ConnectionTester().test({"name": working_db})
        assert result["latency_ms"] < 1000  # in-memory SQLite
        assert result["latency_ms"] >= 0
