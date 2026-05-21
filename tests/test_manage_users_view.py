"""ManageUsersView — paginated user list with create and delete."""
import flet as ft
import pytest

from lib.views.manage.users import ManageUsersView
from tests.conftest import FakePage


_FAKE_USER_1 = {"id": "u1", "username": "alice", "email": "alice@test.com", "roles": ["admin"]}
_FAKE_USER_2 = {"id": "u2", "username": "bob", "email": "bob@test.com", "roles": []}


class _MockAuth:
    def current_user(self):
        return {"id": "1", "username": "admin", "roles": ["admin"]}


class _MockUsers:
    def list(self, page=1, page_size=15):
        return {
            "items": [_FAKE_USER_1, _FAKE_USER_2],
            "total": 2,
            "page": page,
            "page_size": page_size,
            "pages": 1,
        }

    def delete(self, user_id):
        pass

    def create(self, data):
        return {"id": "u3", **data}


class _MockBackend:
    auth = _MockAuth()
    users = _MockUsers()


class _MockUsersEmpty:
    def list(self, page=1, page_size=15):
        return {"items": [], "total": 0, "page": 1, "page_size": 15, "pages": 1}

    def delete(self, user_id):
        pass

    def create(self, data):
        return {"id": "u3", **data}


class _MockBackendEmpty:
    auth = _MockAuth()
    users = _MockUsersEmpty()


class _MockAuthUnauthenticated:
    def current_user(self):
        return None


class _MockBackendUnauthenticated:
    auth = _MockAuthUnauthenticated()


def _make(nav_service, backend=None, route="/manage/users"):
    page = FakePage(route)
    props = {"nav_service": nav_service, "backend": backend or _MockBackend()}
    return ManageUsersView(page, props)


def test_renders_without_crashing(nav_service):
    rendered = _make(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_shows_sidebar(nav_service):
    assert ManageUsersView.show_sidebar is True


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
    page = FakePage("/manage/users")
    view = ManageUsersView(page, {"nav_service": nav_service, "backend": None})
    rendered = view.render()
    assert rendered.controls == []


def test_add_user_empty_fields_shows_error(nav_service):
    view = _make(nav_service)
    view.render()
    view._new_username = ft.TextField(value="")
    view._new_email = ft.TextField(value="")
    view._new_password = ft.TextField(value="")
    view._form_error = ft.Text("")
    view._on_add_user(None)
    assert view._form_error.value == "All fields are required."


def test_add_user_backend_error_shows_error(nav_service):
    class _ErrorUsers(_MockUsers):
        def create(self, data):
            raise ValueError("Username already taken")

    class _ErrorBackend(_MockBackend):
        users = _ErrorUsers()

    view = _make(nav_service, backend=_ErrorBackend())
    view.render()
    view._new_username = ft.TextField(value="alice")
    view._new_email = ft.TextField(value="alice@test.com")
    view._new_password = ft.TextField(value="secret")
    view._form_error = ft.Text("")
    view._body = ft.Column([])
    view._on_add_user(None)
    assert "already taken" in view._form_error.value
