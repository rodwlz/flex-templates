from urllib.parse import urlparse

import flet as ft
from fastapi import FastAPI

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
    # Vault starts LOCKED. SecurityView unlocks it; vault.unlocked event wires connections.
    def _on_vault_unlocked(_event):
        """Re-register vault-sourced DB and cache connections after user unlocks vault."""
        for key in vault.keys():
            if key.startswith("DATABASE_"):
                db_name = key[len("DATABASE_"):].lower()
                try:
                    ConnectionRegistry.register(url=vault.get(key), name=db_name)
                except Exception as e:
                    print(f"Warning: vault DB '{db_name}': {e}")
        _register_caches_from_vault(vault)

    event_bus.subscribe("vault.unlocked", _on_vault_unlocked)

    # ── HTTP API server (Phase 4) ──────────────────────────────────────────
    # Auto-discovers route modules from lib/api/routes/ and serves them on
    # config.api_host:config.api_port in a daemon thread. Same Python process,
    # same ConnectionRegistry — Flet UI and HTTP API share state.
    api_app = FastAPI(title=config.app_title)
    api_app.middleware("http")(log_requests)
    mount_routes(api_app)
    server = BackendServer(api_app, host=config.api_host, port=config.api_port)
    server.start()

    # ── Background task scheduler ──────────────────────────────────────────
    # Jobs run in daemon threads. Add recurring jobs before scheduler.start().
    scheduler = TaskScheduler()
    # scheduler.add_job(some_cleanup_func, "interval", hours=24)
    scheduler.start()

    # ── Database setup — failures here degrade gracefully (app still opens).
    _startup_error: str | None = None
    user_repo = None
    try:
        db_url = config.postgres_url or vault.get("POSTGRES_URL", config.database_url)
        ConnectionRegistry.register(url=db_url, name="postgres")
        user_repo = UserRepository(ConnectionRegistry.get("postgres"))
    except Exception as exc:
        _startup_error = str(exc)

    # ── Backend service adapter (must be initialized before props_factory) ──
    try:
        _backend_factory = ConnectionRegistry.get("postgres")
    except RuntimeError:
        _backend_factory = SessionFactory("sqlite:///./dev.db")
    backend = ServiceBackendAdapter(
        factory=_backend_factory,
        user_service=UserService(_backend_factory),
        scheduler=scheduler,
    )

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
        "backend":           backend,
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
            ft.run(main=flet_main)
    finally:
        server.stop()
        scheduler.stop()


if __name__ == "__main__":
    main()
