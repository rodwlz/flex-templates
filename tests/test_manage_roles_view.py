"""ManageRolesView — role list with create and delete."""
import flet as ft
import pytest

from lib.views.manage.roles import ManageRolesView
from tests.conftest import FakePage


_FAKE_ROLE_1 = {"id": "r1", "name": "admin", "description": "Administrator"}
_FAKE_ROLE_2 = {"id": "r2", "name": "viewer", "description": None}


class _MockBackend:
    def current_user(self):
        return {"id": "1", "username": "admin", "roles": ["admin"]}

    def list_roles(self):
        return [_FAKE_ROLE_1, _FAKE_ROLE_2]

    def create_role(self, name):
        return {"id": "r3", "name": name}

    def delete_role(self, role_id):
        pass


class _MockBackendEmpty:
    def current_user(self):
        return {"id": "1", "username": "admin", "roles": ["admin"]}

    def list_roles(self):
        return []


class _MockBackendUnauthenticated:
    def current_user(self):
        return None


def _make(nav_service, backend=None, route="/manage/roles"):
    page = FakePage(route)
    props = {"nav_service": nav_service, "backend": backend or _MockBackend()}
    return ManageRolesView(page, props)


def test_renders_without_crashing(nav_service):
    rendered = _make(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_shows_sidebar(nav_service):
    assert ManageRolesView.show_sidebar is True


def test_body_is_set_after_render(nav_service):
    view = _make(nav_service)
    view.render()
    assert view._body is not None


def test_body_has_table_control(nav_service):
    view = _make(nav_service)
    view.render()
    assert len(view._body.controls) == 1


def test_empty_state_renders_without_crashing(nav_service):
    rendered = _make(nav_service, backend=_MockBackendEmpty()).render()
    assert isinstance(rendered, ft.View)


def test_protected_redirects_when_unauthenticated(nav_service):
    rendered = _make(nav_service, backend=_MockBackendUnauthenticated()).render()
    assert rendered.controls == []


def test_protected_redirects_when_no_backend(nav_service):
    page = FakePage("/manage/roles")
    view = ManageRolesView(page, {"nav_service": nav_service, "backend": None})
    rendered = view.render()
    assert rendered.controls == []


def test_create_role_empty_name_shows_error(nav_service):
    view = _make(nav_service)
    view.render()
    view._role_name_field.value = ""
    view._on_create_role(None)
    assert "required" in view._error_text.value.lower()


def test_create_role_backend_error_shows_error(nav_service):
    class _ErrorBackend(_MockBackend):
        def create_role(self, name):
            raise ValueError("Role already exists")

    view = _make(nav_service, backend=_ErrorBackend())
    view.render()
    view._role_name_field.value = "admin"
    view._body = ft.Column([])
    view._on_create_role(None)
    assert "already exists" in view._error_text.value
