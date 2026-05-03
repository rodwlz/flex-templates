"""CacheTester: ping a cache adapter for liveness and latency."""
from unittest.mock import MagicMock
import pytest

from lib.services.cache_tester import CacheTester
from lib.contracts.base import ActionRequest, ActionResult


@pytest.fixture
def working_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"keys": ["k1", "k2", "k3"]}
    )
    return adapter


@pytest.fixture
def empty_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(success=True, data={"keys": []})
    return adapter


@pytest.fixture
def failing_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=False, error="AUTH failed: invalid password"
    )
    return adapter


@pytest.fixture
def crashing_adapter():
    adapter = MagicMock()
    adapter.execute.side_effect = ConnectionError("Connection refused")
    return adapter


class TestCacheTester:
    def test_returns_alive_true_with_keycount(self, working_adapter):
        result = CacheTester(working_adapter).test({})
        assert result["alive"] is True
        assert result["latency_ms"] >= 0
        assert result["info"] == "3 keys"
        assert result["error"] is None

    def test_returns_alive_with_zero_keys(self, empty_adapter):
        result = CacheTester(empty_adapter).test({})
        assert result["alive"] is True
        assert result["info"] == "0 keys"

    def test_returns_alive_false_on_failed_action(self, failing_adapter):
        result = CacheTester(failing_adapter).test({})
        assert result["alive"] is False
        assert result["latency_ms"] is None
        assert "AUTH failed" in result["error"]

    def test_returns_alive_false_on_exception(self, crashing_adapter):
        result = CacheTester(crashing_adapter).test({})
        assert result["alive"] is False
        assert result["latency_ms"] is None
        assert "Connection refused" in result["error"]

    def test_never_raises(self, crashing_adapter):
        # Even with broken adapter, returns dict — never throws.
        result = CacheTester(crashing_adapter).test({})
        assert isinstance(result, dict)
        assert set(result.keys()) == {"alive", "latency_ms", "info", "error"}

    def test_via_execute_returns_action_result(self, working_adapter):
        tester = CacheTester(working_adapter)
        result = tester.execute(ActionRequest(action="test", data={}))
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.data["alive"] is True
