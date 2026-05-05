"""SimpleService dispatch contract.

Every SimpleService subclass relies on this base class for action routing,
return-value wrapping, and exception trapping. These tests pin down the exact
contract:

    * ``execute(ActionRequest(action="x"))`` calls ``self.x(data)``
    * Plain-dict returns become ``ActionResult(success=True, data=<dict>)``
    * ``ActionResult`` returns pass through unchanged
    * Exceptions become ``ActionResult(success=False, error=str(exc))``
    * Unknown / private action names fail cleanly

Read these tests as the authoritative spec for what SimpleService does.
"""
import pytest

from lib.contracts.base import ActionRequest, ActionResult, Event
from lib.core.interfaces import IService, SimpleService


class _Demo(SimpleService):
    """Tiny SimpleService used as the system-under-test."""

    def echo(self, data: dict) -> dict:
        return {"echoed": data.get("msg", "")}

    def explicit(self, data: dict) -> ActionResult:
        return ActionResult(
            success=True,
            data={"explicit": True},
            events=[Event(type="demo.explicit", payload={})],
        )

    def boom(self, data: dict) -> dict:
        raise RuntimeError("kaboom")

    def silent(self, data: dict) -> None:
        return None

    def _private(self, data: dict) -> dict:
        return {"should_not": "reach"}


# ── Routing by action name ────────────────────────────────────────────────

def test_routes_action_to_same_named_method():
    result = _Demo().execute(ActionRequest(action="echo", data={"msg": "hi"}))
    assert result.success is True
    assert result.data == {"echoed": "hi"}


def test_unknown_action_returns_failed_result():
    result = _Demo().execute(ActionRequest(action="does_not_exist"))
    assert result.success is False
    assert "does_not_exist" in result.error


def test_empty_action_returns_failed_result():
    result = _Demo().execute(ActionRequest(action=""))
    assert result.success is False
    assert "Unknown action" in result.error


def test_underscore_prefixed_action_is_blocked():
    # Private methods must not be reachable through dispatch.
    result = _Demo().execute(ActionRequest(action="_private"))
    assert result.success is False
    assert "_private" in result.error


def test_attribute_that_is_not_callable_is_rejected():
    """A class attribute (non-method) must not be invokable as an action."""

    class WithAttr(SimpleService):
        not_callable = "I am a string"

    result = WithAttr().execute(ActionRequest(action="not_callable"))
    assert result.success is False
    assert "Unknown action" in result.error


# ── Return-value wrapping ──────────────────────────────────────────────────

def test_dict_return_becomes_successful_action_result():
    result = _Demo().execute(ActionRequest(action="echo", data={"msg": "x"}))
    assert isinstance(result, ActionResult)
    assert result.success is True
    assert result.data == {"echoed": "x"}
    assert result.error is None


def test_action_result_return_passes_through_unchanged():
    result = _Demo().execute(ActionRequest(action="explicit"))
    assert result.success is True
    assert result.data == {"explicit": True}
    assert len(result.events) == 1
    assert result.events[0].type == "demo.explicit"


def test_none_return_becomes_successful_empty_result():
    result = _Demo().execute(ActionRequest(action="silent"))
    assert result.success is True
    assert result.data == {}
    assert result.error is None


# ── Exception trapping ─────────────────────────────────────────────────────

def test_exception_becomes_failed_action_result():
    result = _Demo().execute(ActionRequest(action="boom"))
    assert result.success is False
    assert "kaboom" in result.error


def test_caller_never_sees_raw_exception():
    """SimpleService.execute must NEVER propagate — that's its purpose."""
    try:
        _Demo().execute(ActionRequest(action="boom"))
    except Exception:
        pytest.fail("execute() leaked an exception to the caller")


# ── IService base ─────────────────────────────────────────────────────────

def test_iservice_cannot_be_instantiated_directly():
    """IService is abstract — subclasses must implement execute()."""
    with pytest.raises(TypeError):
        IService()  # noqa  — abstract instantiation should fail


def test_simple_service_satisfies_iservice():
    """A SimpleService instance is also an IService."""
    assert isinstance(_Demo(), IService)
