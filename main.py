from urllib.parse import urlparse

import flet as ft
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lib.config.settings import AppConfig
from lib.core.events import EventBus, Events
from lib.services.navigation_service import NavigationService
from lib.services.nav import Nav
from lib.services.cache_registry import CacheRegistry
from lib.services.cache_tester import CacheTester
from lib.services.connection_tester import ConnectionTester
from lib.security.vault_service import VaultService
from lib.security.vault_store import VaultStore
from lib.security.vault import Vault
from lib.ui.adapter import FletNavigationAdapter
from lib.ui.router import FletRouter
from lib.ui.error_adapter import FletErrorAdapter
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.adapters.redis_adapter import RedisAdapter
from lib.repositories.user_repository import UserRepository
from lib.api.server import BackendServer
from lib.api.router_registry import mount_routes
from lib.middleware.logging import setup_logging, log_requests
from lib.tasks.scheduler import TaskScheduler
from lib.adapters.backend_adapter import ServiceBackendAdapter
from lib.services.user_service import UserService
from lib.services.product_service import ProductService
from lib.database.base import Base
from lib.email.console_sender import ConsoleSender
from lib.email.smtp_sender import SmtpSender


# Vault key prefix → adapter builder. Adding a new cache type means adding one
# entry here. The convention is {SERVICE}_URL[_{ID}] + {SERVICE}_PASSWORD[_{ID}].
_CACHE_BUILDERS = {
    "REDIS": lambda host, port, password: RedisAdapter(
        host=host, port=port or 6379, password=password or ""
    ),
}


def _register_caches_from_vault(vault) -> None:
    """Scan vault keys for SERVICE_URL[_ID] and register matching adapters."""
    for key in vault.keys():
        if "_URL" not in key:
            continue
        service, _, id_suffix = key.partition("_URL")
        builder = _CACHE_BUILDERS.get(service)
        if builder is None:
            continue

        id_part = id_suffix.lstrip("_").lower()
        registry_name = f"{service.lower()}_{id_part}" if id_part else service.lower()
        password_key = (
            f"{service}_PASSWORD_{id_part.upper()}" if id_part else f"{service}_PASSWORD"
        )
        try:
            parsed = urlparse(vault.get(key))
            adapter = builder(parsed.hostname, parsed.port, vault.get(password_key, ""))
            CacheRegistry.register(registry_name, adapter)
        except Exception as e:
            print(f"Warning: Failed to register cache '{registry_name}': {e}")


def main():
    config = AppConfig()
    setup_logging("DEBUG" if config.debug else "INFO")

    # Instantiate email sender based on configuration
    email_sender = SmtpSender(config) if config.email_sender == "smtp" else ConsoleSender()

    # Register all databases from DATABASE_* environment variables
    for db_name, db_url in config.databases.items():
        try:
            ConnectionRegistry.register(url=db_url, name=db_name)
        except Exception as e:
            print(f"Warning: Failed to register database '{db_name}': {e}")

    event_bus = EventBus()
    nav_service = NavigationService(event_bus)
    nav_adapter = FletNavigationAdapter(nav_service)
    error_adapter = FletErrorAdapter()
    router = FletRouter(nav_service, views_package="lib.views")

    # Stateless probe singletons — look up their target by name in the registry.
    connection_tester = ConnectionTester()
    cache_tester      = CacheTester()

    nav    = Nav(nav_service)
    events = Events(event_bus)

    # Vault for secrets management (DB passwords, API keys, etc.)
    # Keys live in `.secrets/.env` — the vault service reads/writes that file
    # itself, so first launch can bootstrap with no manual setup.
    vault_service = VaultService(
        store=VaultStore(path=config.vault_path),
        master_key=config.vault_master_key,
        confirm_key=config.vault_confirm_key,
        env_path=config.vault_env_path,
    )

    # Parameterized routes (path params).  Convention routing handles the rest.
    router.register("/products/{id}", "lib.views.product_detail")
    router.register("/admin/databases", "lib.views.admin.databases")
    router.register("/admin/caches",   "lib.views.admin.caches")
    router.register("/manage/users",    "lib.views.manage.users")
    router.register("/manage/roles",    "lib.views.manage.roles")
    router.register("/admin/scheduler", "lib.views.admin.scheduler")

    vault = Vault(vault_service)

    # ── Background task scheduler ──────────────────────────────────────────
    # Jobs run in daemon threads. Add recurring jobs before scheduler.start().
    scheduler = TaskScheduler()
    # scheduler.add_job(some_cleanup_func, "interval", hours=24)
    scheduler.start()

    # ── Backend adapter — mutable so vault unlock can re-wire to a real DB ──
    # _ctx holds live references that closures below can rebind after vault unlock.
    _ctx: dict = {}

    def _make_backend(factory):
        return ServiceBackendAdapter(
            factory=factory,
            user_service=UserService(factory, email_sender=email_sender),
            scheduler=scheduler,
        )

    _startup_error: str | None = None
    user_repo = None
    try:
        _primary_factory = ConnectionRegistry.get(config.primary_database)
        user_repo = UserRepository(_primary_factory)
        _ctx["backend"] = _make_backend(_primary_factory)
        _ctx["product_service"] = ProductService(_primary_factory)
    except RuntimeError:
        # primary DB not yet registered — fall back to local SQLite
        _sqlite_factory = SessionFactory("sqlite:///./dev.db")
        # Run outstanding Alembic migrations; fall back to create_tables if Alembic fails.
        try:
            from alembic.config import Config as AlembicConfig
            from alembic import command as alembic_cmd
            alembic_cmd.upgrade(AlembicConfig("alembic.ini"), "head")
        except Exception as _alembic_err:
            print(f"Warning: Alembic failed, using create_tables: {_alembic_err}")
            _sqlite_factory.create_tables(Base)
        _ctx["backend"] = _make_backend(_sqlite_factory)
        _ctx["product_service"] = ProductService(_sqlite_factory)
    except Exception as exc:
        _startup_error = str(exc)
        _ctx["backend"] = None
        _ctx["product_service"] = None

    # Vault starts LOCKED. SecurityView unlocks it; vault.unlocked event wires connections.
    def _on_vault_unlocked(_event):
        """Re-register vault-sourced DB/cache connections; re-wire backend if primary DB arrives."""
        for key in vault.keys():
            if key.startswith("DATABASE_"):
                db_name = key[len("DATABASE_"):].lower()
                try:
                    ConnectionRegistry.register(url=vault.get(key), name=db_name)
                except Exception as e:
                    print(f"Warning: vault DB '{db_name}': {e}")
        _register_caches_from_vault(vault)
        # If the primary DB just became available (e.g. DATABASE_POSTGRES in vault),
        # replace the SQLite backend adapter with the real one — no restart needed.
        try:
            pf = ConnectionRegistry.get(config.primary_database)
            _ctx["backend"] = _make_backend(pf)
            _ctx["product_service"] = ProductService(pf)
        except RuntimeError:
            pass

    event_bus.subscribe("vault.unlocked", _on_vault_unlocked)

    # ── HTTP API server (Phase 4) ──────────────────────────────────────────
    # Auto-discovers route modules from lib/api/routes/ and serves them on
    # config.api_host:config.api_port in a daemon thread. Same Python process,
    # same ConnectionRegistry — Flet UI and HTTP API share state.
    api_app = FastAPI(title=config.app_title)
    api_app.middleware("http")(log_requests)
    _cors_origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    mount_routes(api_app, config)
    from lib.api.routes import scheduler as scheduler_routes
    scheduler_routes.set_scheduler(scheduler)
    from lib.api.routes.auth import set_email_sender as _set_auth_email_sender
    _set_auth_email_sender(email_sender)
    from lib.api.websocket.manager import ConnectionManager
    from lib.api.routes import ws as ws_route
    _ws_manager = ConnectionManager()
    ws_route.set_manager(_ws_manager)
    server = BackendServer(api_app, host=config.api_host, port=config.api_port)
    server.start()

    router.set_props_factory(lambda: {
        # ── Simple snap-in API (use these in your views and services) ──────
        "nav":    nav,
        "vault":  vault,
        "events": events,
        # ── Full service API (used by framework internals) ─────────────────
        "nav_service":   nav_service,
        "vault_service": vault_service,
        # ── Data access (repositories & services) ───────────────────────────
        "user_repo":         user_repo,
        "redis":             CacheRegistry._adapters.get("redis"),
        "config":            config,
        "connection_tester": connection_tester,
        "cache_tester":      cache_tester,
        "backend":           _ctx.get("backend"),
        "product_service":   _ctx.get("product_service"),
        "ws_manager":        _ws_manager,
        # ── Dev tooling ────────────────────────────────────────────────────
        "dev_nav": True,  # orange FAB — remove for production
    })

    def flet_main(page: ft.Page):
        page.title = config.app_title
        page.theme_mode = ft.ThemeMode.DARK
        nav_adapter.bind_page(page)
        error_adapter.bind_page(page)
        page.on_route_change = lambda e: router.route_change(page)
        page.on_view_pop = lambda e: router.view_pop(page)

        if _startup_error:
            error_adapter.show_error(f"DB unavailable: {_startup_error}")

        # Flet quirk: page.go(page.route) is a no-op when the route hasn't
        # changed (e.g. initial '/' is already '/'), so on_route_change never
        # fires and the screen stays blank. Render the first view directly.
        router.route_change(page)

    try:
        if config.api_only:
            import signal, threading
            _stop = threading.Event()
            signal.signal(signal.SIGTERM, lambda *_: _stop.set())
            signal.signal(signal.SIGINT, lambda *_: _stop.set())
            print(f"API-only mode — http://{config.api_host}:{config.api_port}")
            _stop.wait()
        else:
            _view_map = {
                "web": ft.AppView.WEB_BROWSER,
                "headless": ft.AppView.HEADLESS_WEB,
            }
            ft.run(
                main=flet_main,
                view=_view_map.get(config.app_view, ft.AppView.FLET_APP),
                port=config.flet_port if config.app_view != "desktop" else 0,
            )
    finally:
        server.stop()
        scheduler.stop()


if __name__ == "__main__":
    main()
