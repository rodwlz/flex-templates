"""
mount_routes — auto-discover and mount every router in lib/api/routes/.

Drop a new file in routes/ that defines `router = APIRouter(...)` and it
gets picked up automatically — no manual registration step.
"""
from __future__ import annotations

import importlib
import pkgutil
from fastapi import FastAPI


def mount_routes(app: FastAPI, package: str = "lib.api.routes") -> None:
    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if hasattr(sub, "router"):
            app.include_router(sub.router)
