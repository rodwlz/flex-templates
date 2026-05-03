"""
BaseView — the abstract page template.

Every view in the app subclasses this. Override `build_content()` (required)
and toggle/swap any of the surrounding pieces:

    class MyView(BaseView):
        title = "My Page"
        show_sidebar = False             # toggle a piece off
        Params = MyParams                # optional Pydantic model

        def build_appbar(self):          # swap a piece for a custom one
            return MyCustomAppBar(...)

        def build_content(self):         # required
            return ft.Column([...])

    def view(page, props):               # router entry point
        return MyView(page, props).render()
"""
from __future__ import annotations

import flet as ft

from lib.ui.components.dev_nav import DevNav
from lib.ui.components.nav_bar import NavBar
from lib.ui.components.side_bar import SideBar


SIDEBAR_ITEMS = [
    ("Home", "/"),
    ("Login", "/login"),
    ("Products", "/products"),
    ("Security", "/security"),
    ("Admin", "/admin/databases"),
]


class BaseView:
    # ── Class-level config (override in subclass) ──────────────────────────
    title: str = "FlexApp"

    show_appbar: bool = True
    show_sidebar: bool = True
    show_bottombar: bool = False

    # Optional: a Pydantic BaseModel subclass.  When set, params (path)
    # and query strings are merged and validated into self.params.
    Params = None

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def __init__(self, page: ft.Page, props: dict):
        self.page = page
        self.props = props
        nav = props.get("nav_service")
        if nav is None:
            raise KeyError(
                f"{type(self).__name__}: props['nav_service'] is required. "
                "Add it to router.set_props_factory()."
            )
        self.nav_service = nav
        # Simple-API shortcuts — available when wired in main.py, None otherwise
        self.nav    = props.get("nav")
        self.vault  = props.get("vault")
        self.events = props.get("events")
        self.params = self._build_params()

    def _build_params(self):
        if self.Params is None:
            return None
        merged = {
            **self.props.get("params", {}),
            **self.props.get("query", {}),
        }
        return self.Params(**merged)

    # ── Overridable pieces ─────────────────────────────────────────────────
    def build_appbar(self):
        return NavBar(self.title, self.nav_service)

    def build_sidebar(self):
        return SideBar(SIDEBAR_ITEMS, self.nav_service)

    def build_bottombar(self):
        return None

    def build_content(self):
        raise NotImplementedError(
            f"{type(self).__name__}.build_content() must be implemented"
        )

    # ── Render ─────────────────────────────────────────────────────────────
    def render(self) -> ft.View:
        body = self._coerce_to_control(self.build_content())
        main_area = ft.Container(content=body, expand=True, padding=30)

        if self.show_sidebar:
            sidebar = self.build_sidebar()
            if sidebar is not None:
                root = ft.Row([sidebar, main_area], expand=True, spacing=0)
            else:
                root = main_area
        else:
            root = main_area

        controls: list[ft.Control] = []
        if self.props.get("dev_nav"):
            controls.append(DevNav(self.nav_service, self.page).build())
        controls.append(root)

        return ft.View(
            route=self.page.route or "/",
            appbar=self.build_appbar() if self.show_appbar else None,
            bottom_appbar=self.build_bottombar() if self.show_bottombar else None,
            controls=controls,
            padding=0,
            spacing=0,
        )

    @staticmethod
    def _coerce_to_control(value) -> ft.Control:
        if isinstance(value, ft.Control):
            return value
        if isinstance(value, list):
            return ft.Column(value, spacing=15)
        return ft.Text(str(value))
