"""CacheTester: probe a registered cache adapter for liveness and latency."""
from unittest.mock import MagicMock
import pytest

from lib.contracts.base import ActionRequest, ActionResult
from lib.services.cache_registry import CacheRegistry
from lib.services.cache_tester import CacheTester


@pytest.fixture(autouse=True)
def clean_registry():
    CacheRegistry._adapters = {}
    yield
    CacheRegistry._adapters = {}


def _register(name: str, adapter):
    CacheRegistry._adapters[name] = adapter
    return name


@pytest.fixture
def working_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"keys": ["k1", "k2", "k3"]}
    )
    return _register("working", adapter)


@pytest.fixture
def empty_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(success=True, data={"keys": []})
    return _register("empty", adapter)


@pytest.fixture
def failing_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=False, error="AUTH failed: invalid password"
    )
    return _register("failing", adapter)


@pytest.fixture
def crashing_adapter():
    adapter = MagicMock()
    adapter.execute.side_effect = ConnectionError("Connection refused")
    return _register("crashing", adapter)


class TestCacheTester:
    def test_returns_alive_true_with_keycount(self, working_adapter):
        result = CacheTester().test({"name": working_adapter})
        assert result["alive"] is True
        assert result["latency_ms"] >= 0
        assert result["info"] == "3 keys"
        assert result["error"] is None

    def test_returns_alive_with_zero_keys(self, empty_adapter):
        result = CacheTester().test({"name": empty_adapter})
        assert result["alive"] is True
        assert result["info"] == "0 keys"

    def test_returns_alive_false_on_failed_action(self, failing_adapter):
        result = CacheTester().test({"name": failing_adapter})
        assert result["alive"] is False
        assert result["latency_ms"] is None
        assert "AUTH failed" in result["error"]

    def test_returns_alive_false_on_exception(self, crashing_adapter):
        result = CacheTester().test({"name": crashing_adapter})
        assert result["alive"] is False
        assert result["latency_ms"] is None
        assert "Connection refused" in result["error"]

    def test_unknown_name_returns_failure(self):
        result = CacheTester().test({"name": "does_not_exist"})
        assert result["alive"] is False
        assert result["error"] is not None

    def test_never_raises(self, crashing_adapter):
        result = CacheTester().test({"name": crashing_adapter})
        assert isinstance(result, dict)
        assert set(result.keys()) == {"alive", "latency_ms", "info", "error"}

    def test_via_execute_returns_action_result(self, working_adapter):
        tester = CacheTester()
        result = tester.execute(ActionRequest(action="test", data={"name": working_adapter}))
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.data["alive"] is True
