"""ProtectedView — auth guard base class tests."""
import flet as ft
import pytest

from lib.ui.layouts.protected_view import ProtectedView
from tests.conftest import FakePage


class _MockBackendLoggedIn:
    def current_user(self):
        return {"id": "1", "username": "alice", "roles": []}


class _MockBackendLoggedOut:
    def current_user(self):
        return None


class _ContentView(ProtectedView):
    title = "Secret"

    def build_content(self):
        return ft.Text("secret content")


def _make(route, backend, nav_service):
    page = FakePage(route)
    props = {"nav_service": nav_service, "backend": backend}
    return _ContentView(page, props)


def test_renders_normally_when_logged_in(nav_service):
    v = _make("/secret", _MockBackendLoggedIn(), nav_service)
    result = v.render()
    assert result.appbar is not None


def test_redirects_to_login_when_logged_out(nav_service):
    v = _make("/secret", _MockBackendLoggedOut(), nav_service)
    result = v.render()
    assert result.controls == []


def test_redirect_returns_view_with_current_route(nav_service):
    v = _make("/manage/users", _MockBackendLoggedOut(), nav_service)
    result = v.render()
    assert result.route == "/manage/users"


def test_redirects_when_backend_key_missing(nav_service):
    page = FakePage("/secret")
    props = {"nav_service": nav_service}  # no "backend" key
    v = _ContentView(page, props)
    result = v.render()
    assert result.controls == []
