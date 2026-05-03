"""
mount_service — auto-generate HTTP POST routes from any SimpleService.

One line exposes a whole service over HTTP. The HTTP API and Flet UI both
go through `service.execute(ActionRequest)` so the contract stays identical.

Usage:
    from lib.api.mount_service import mount_service

    app.include_router(mount_service(user_service, prefix="/users"))
    # POST /users/create  {data}  → ActionResult JSON
    # POST /users/get     {data}  → ActionResult JSON

Skip list: execute (the dispatcher itself) plus stage/confirm/cancel
(StagingService — those need HTTP context the auto-router can't infer).
For path-param REST endpoints (GET /users/{id}), write a manual APIRouter
in lib/api/routes/.
"""
from __future__ import annotations

from fastapi import APIRouter, Body

from lib.contracts.base import ActionRequest
from lib.core.interfaces import SimpleService


_SKIP = {"execute", "stage", "confirm", "cancel"}


def mount_service(service: SimpleService, prefix: str) -> APIRouter:
    router = APIRouter(prefix=prefix)

    cls = type(service)
    actions = [
        name for name in dir(cls)
        if not name.startswith("_")
        and name not in _SKIP
        and callable(getattr(cls, name, None))
    ]

    for action in actions:
        def make_handler(act: str):
            async def handler(data: dict = Body(default_factory=dict)):
                result = service.execute(ActionRequest(action=act, data=data))
                return result.model_dump()
            handler.__name__ = act
            return handler

        router.add_api_route(f"/{action}", make_handler(action), methods=["POST"])

    return router
