from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class Event(BaseModel):
    type: str
    payload: dict[str, Any] = {}


class ActionRequest(BaseModel):
    action: str
    data: dict[str, Any] = {}


class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    events: list[Event] = []
    error: str | None = None
