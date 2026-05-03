import os
import flet as ft

from lib.core.events import EventBus, Events
from lib.services.navigation_service import NavigationService
from lib.services.nav import Nav
from lib.security.vault_service import VaultService
from lib.security.vault_store import VaultStore
from lib.security.vault import Vault
from lib.ui.adapter import FletNavigationAdapter
from lib.ui.router import FletRouter


def main():
    event_bus = EventBus()
    nav_service = NavigationService(event_bus)
    nav_adapter = FletNavigationAdapter(nav_service)
    router = FletRouter(nav_service, views_package="lib.views")

    nav    = Nav(nav_service)
    events = Events(event_bus)

    # Vault for secrets management (DB passwords, API keys, etc.)
    # Keys live in `.secrets/.env` — the vault service reads/writes that file
    # itself, so first launch can bootstrap with no manual setup. Project-root
    # env vars still win if set (useful for dev/CI overrides).
    vault_service = VaultService(
        store=VaultStore(path=".secrets/vault.json"),
        master_key=os.getenv("VAULT_MASTER_KEY", ""),
        confirm_key=os.getenv("VAULT_CONFIRM_KEY", ""),
        env_path=".secrets/.env",
    )

    # Parameterized routes (path params).  Convention routing handles the rest.
    router.register("/products/{id}", "lib.views.product_detail")

    vault = Vault(vault_service)

    router.set_props_factory(lambda: {
        # ── Simple snap-in API (use these in your views and services) ──────
        "nav":    nav,
        "vault":  vault,
        "events": events,
        # ── Full service API (used by framework internals) ─────────────────
        "nav_service":   nav_service,
        "vault_service": vault_service,
        # ── Dev tooling ────────────────────────────────────────────────────
        "dev_nav": True,  # orange FAB — remove for production
    })

    def flet_main(page: ft.Page):
        page.title = "FlexTemplates"
        page.theme_mode = ft.ThemeMode.DARK
        nav_adapter.bind_page(page)
        page.on_route_change = lambda e: router.route_change(page)
        page.on_view_pop = lambda e: router.view_pop(page)

        # Flet quirk: page.go(page.route) is a no-op when the route hasn't
        # changed (e.g. initial '/' is already '/'), so on_route_change never
        # fires and the screen stays blank. Render the first view directly.
        router.route_change(page)

    ft.run(main=flet_main)


if __name__ == "__main__":
    main()
