from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class Event(BaseModel):
    type: str
    payload: dict[str, Any] = {}


class ActionRequest(BaseModel):
    action: str
    data: dict[str, Any] = {}
    requires_approval: bool = Field(default=False, description="Flag for operations requiring explicit confirmation")


class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    events: list[Event] = []
    error: str | None = None


class PaginatedResult(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    pages: int
