"""
V1 contract router — the single guard for the entire /v1/ API surface.

Every route module mounts through one of two sub-routers returned by
make_v1_router():

  public    — rate-limited at login rate; no Bearer required (login endpoint)
  protected — rate-limited at general rate + Bearer JWT required (all other routes)

Usage (in router_registry.py):
    v1_router, public, protected = make_v1_router(config)
    public.include_router(auth_routes.router)      # _PUBLIC_ROUTER = True
    protected.include_router(users_routes.router)
    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from lib.api.rate_limiter import RateLimiter
from lib.auth.dependencies import get_current_user


def make_v1_router(config) -> tuple[APIRouter, APIRouter, APIRouter]:
    """
    Build the /v1 contract router.

    Returns (v1_router, public, protected). Mount route modules into public or
    protected, include both into v1_router, then include v1_router into the app.
    """
    general_limiter = RateLimiter(limit=config.rate_limit_per_minute)
    login_limiter = RateLimiter(limit=config.rate_limit_login_per_minute)

    v1_router = APIRouter(prefix="/v1")
    public = APIRouter(dependencies=[Depends(login_limiter)])
    protected = APIRouter(
        dependencies=[Depends(general_limiter), Depends(get_current_user)]
    )

    return v1_router, public, protected
