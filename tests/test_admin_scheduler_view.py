"""AdminSchedulerView — read-only scheduler inspector."""
import flet as ft
import pytest

from lib.views.admin.scheduler import AdminSchedulerView
from tests.conftest import FakePage


_FAKE_JOB = {
    "id": "job_heartbeat",
    "func_name": "tasks.heartbeat",
    "trigger": "interval[0:01:00]",
    "next_run_time": "2026-05-20 12:00:00",
}


class _MockAuth:
    def current_user(self):
        return {"id": "1", "username": "admin", "roles": ["admin"]}


class _MockScheduler:
    def list(self):
        return [_FAKE_JOB]


class _MockBackend:
    auth = _MockAuth()
    scheduler = _MockScheduler()


class _MockSchedulerEmpty:
    def list(self):
        return []


class _MockBackendEmpty:
    auth = _MockAuth()
    scheduler = _MockSchedulerEmpty()


class _MockAuthUnauthenticated:
    def current_user(self):
        return None


class _MockBackendUnauthenticated:
    auth = _MockAuthUnauthenticated()


def _make(nav_service, backend=None, route="/admin/scheduler"):
    page = FakePage(route)
    props = {"nav_service": nav_service, "backend": backend or _MockBackend()}
    return AdminSchedulerView(page, props)


def test_renders_without_crashing(nav_service):
    rendered = _make(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_has_correct_title(nav_service):
    assert AdminSchedulerView.title == "Scheduler"


def test_shows_sidebar(nav_service):
    assert AdminSchedulerView.show_sidebar is True


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
    page = FakePage("/admin/scheduler")
    view = AdminSchedulerView(page, {"nav_service": nav_service, "backend": None})
    rendered = view.render()
    assert rendered.controls == []
