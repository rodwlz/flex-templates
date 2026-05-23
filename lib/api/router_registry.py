"""
mount_routes — auto-discover and mount every router in lib/api/routes/.

Each route module is mounted through the v1 contract router:
  - Modules with _PUBLIC_ROUTER = True → public sub-router (rate limited, no auth)
  - All other modules → protected sub-router (rate limited + Bearer JWT)

Drop a new file in routes/ that defines `router = APIRouter(...)` and it is
protected automatically — no manual registration, no forgotten auth.
"""
from __future__ import annotations

import importlib
import pkgutil
from fastapi import FastAPI


def mount_routes(app: FastAPI, config, package: str = "lib.api.routes") -> None:
    from lib.api.v1 import make_v1_router
    v1_router, public, protected = make_v1_router(config)

    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if hasattr(sub, "public_router"):
            public.include_router(sub.public_router)
        if hasattr(sub, "router"):
            target = public if getattr(sub, "_PUBLIC_ROUTER", False) else protected
            target.include_router(sub.router)

    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
