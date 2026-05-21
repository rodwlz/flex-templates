"""ProtectedView — auth guard.

Subclass instead of BaseView for any view that requires login.
Redirects to /login if backend.current_user() returns None.
"""
from __future__ import annotations

import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView


class ProtectedView(BaseView):
    """Base class for views requiring authentication.

    render() checks backend.auth.current_user() before calling build_content().
    Returns an empty View (triggering a /login redirect) if not authenticated.
    """

    def render(self) -> ft.View:
        backend = self.props.get("backend")
        if not backend or not backend.auth.current_user():
            self.nav_service.execute(
                ActionRequest(action="visit", data={"url": "/login"})
            )
            return ft.View(route=self.page.route or "/", controls=[])
        return super().render()
