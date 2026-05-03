"""Contracts: the 'plugs' every layer talks through. Must stay rigid."""
import pytest
from pydantic import ValidationError

from lib.contracts.base import ActionRequest, ActionResult, Event


def test_action_request_only_needs_an_action():
    req = ActionRequest(action="visit")
    assert req.action == "visit"
    assert req.data == {}


def test_action_request_carries_data():
    req = ActionRequest(action="create_user", data={"name": "Alice"})
    assert req.data == {"name": "Alice"}


def test_action_result_success_path():
    result = ActionResult(success=True, data={"id": 42})
    assert result.success is True
    assert result.data["id"] == 42
    assert result.error is None


def test_action_result_error_path():
    result = ActionResult(success=False, error="DB unreachable")
    assert result.success is False
    assert result.error == "DB unreachable"


def test_event_carries_type_and_payload():
    event = Event(type="user.created", payload={"id": 1})
    assert event.type == "user.created"
    assert event.payload["id"] == 1


def test_action_request_rejects_missing_action():
    with pytest.raises(ValidationError):
        ActionRequest()  # action is required
