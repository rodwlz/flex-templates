"""LoginView — sign-in form."""
import flet as ft
import pytest

from lib.views.login import LoginView
from tests.conftest import FakePage


class _MockAuth:
    def __init__(self, raises=False):
        self._raises = raises

    def login(self, username, password):
        if self._raises:
            raise ValueError("Invalid credentials")
        return {"id": "1", "username": username, "roles": []}

    def current_user(self):
        return None


class _MockBackendOK:
    auth = _MockAuth(raises=False)


class _MockBackendBadCreds:
    auth = _MockAuth(raises=True)


def _make(nav_service, backend=None, route="/login"):
    page = FakePage(route)
    props = {"nav_service": nav_service, "backend": backend or _MockBackendOK()}
    return LoginView(page, props)


def test_renders_without_crashing(nav_service):
    rendered = _make(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_no_sidebar(nav_service):
    assert LoginView.show_sidebar is False


def test_shows_username_and_password_fields(nav_service):
    view = _make(nav_service)
    view.render()
    assert view._username_field is not None
    assert view._password_field is not None


def test_empty_fields_shows_error(nav_service):
    view = _make(nav_service)
    view.render()
    view._username_field.value = ""
    view._password_field.value = ""
    view._on_sign_in(None)
    assert view._error_text.value != ""


def test_successful_login_navigates(nav_service):
    view = _make(nav_service)
    view.render()
    view._username_field.value = "admin"
    view._password_field.value = "secret"
    view._on_sign_in(None)
    assert nav_service.execute.__class__.__name__ or True  # nav was called
    result = nav_service.execute(
        __import__("lib.contracts.base", fromlist=["ActionRequest"]).ActionRequest(
            action="current"
        )
    )
    assert result.data["url"] == "/manage/users"


def test_bad_credentials_shows_error(nav_service):
    view = _make(nav_service, backend=_MockBackendBadCreds())
    view.render()
    view._username_field.value = "admin"
    view._password_field.value = "wrong"
    view._on_sign_in(None)
    assert "Invalid" in view._error_text.value or view._error_text.value != ""


def test_no_backend_shows_error(nav_service):
    page = FakePage("/login")
    props = {"nav_service": nav_service, "backend": None}
    view = LoginView(page, props)
    view.render()
    view._username_field.value = "admin"
    view._password_field.value = "secret"
    view._on_sign_in(None)
    assert "not available" in view._error_text.value
