"""BaseView: the page template. Toggles, swaps, and typed params."""
import flet as ft
import pytest
from pydantic import BaseModel, ValidationError

from lib.ui.layouts.base_view import BaseView
from tests.conftest import FakePage


# ── Helper: minimal subclass with required build_content ───────────────────
class HelloView(BaseView):
    title = "Hello"

    def build_content(self):
        return ft.Text("hi")


def make_view(view_cls, route="/", path_params=None, query=None, nav_service=None):
    """Build a view instance with sensible defaults for tests."""
    page = FakePage(route)
    props = {
        "nav_service": nav_service,
        "params": path_params or {},
        "query": query or {},
    }
    return view_cls(page, props)


# ── Defaults ───────────────────────────────────────────────────────────────

def test_default_view_has_appbar(nav_service):
    v = make_view(HelloView, nav_service=nav_service).render()
    assert v.appbar is not None


def test_default_view_has_sidebar_inside_a_row(nav_service):
    v = make_view(HelloView, nav_service=nav_service).render()
    root = v.controls[0]
    assert isinstance(root, ft.Row)  # Row(sidebar, content)


# ── Toggles ────────────────────────────────────────────────────────────────

def test_show_appbar_false_removes_appbar(nav_service):
    class NoAppbar(HelloView):
        show_appbar = False

    v = make_view(NoAppbar, nav_service=nav_service).render()
    assert v.appbar is None


def test_show_sidebar_false_removes_sidebar(nav_service):
    class NoSidebar(HelloView):
        show_sidebar = False

    v = make_view(NoSidebar, nav_service=nav_service).render()
    root = v.controls[0]
    assert not isinstance(root, ft.Row)  # no sidebar wrapper


def test_show_bottombar_true_calls_build_bottombar(nav_service):
    class WithBottom(HelloView):
        show_bottombar = True

        def build_bottombar(self):
            return ft.AppBar(title=ft.Text("bottom"))

    v = make_view(WithBottom, nav_service=nav_service).render()
    assert v.bottom_appbar is not None


# ── Swappable parts ────────────────────────────────────────────────────────

def test_overriding_build_appbar_swaps_in_a_custom_one(nav_service):
    custom = ft.AppBar(title=ft.Text("CUSTOM"))

    class Custom(HelloView):
        def build_appbar(self):
            return custom

    v = make_view(Custom, nav_service=nav_service).render()
    assert v.appbar is custom


def test_build_content_is_required(nav_service):
    class Broken(BaseView):
        pass  # forgot build_content

    instance = make_view(Broken, nav_service=nav_service)

    with pytest.raises(NotImplementedError):
        instance.render()


# ── Typed params (Pydantic) ────────────────────────────────────────────────

class ProductParams(BaseModel):
    id: int
    tab: str = "overview"


class ProductView(HelloView):
    Params = ProductParams


def test_no_params_class_means_self_params_is_none(nav_service):
    instance = make_view(HelloView, nav_service=nav_service)
    assert instance.params is None


def test_path_params_get_typed_via_pydantic(nav_service):
    instance = make_view(
        ProductView, nav_service=nav_service, path_params={"id": "42"}
    )
    assert instance.params.id == 42  # coerced from str → int
    assert isinstance(instance.params.id, int)


def test_query_params_fill_in_when_path_params_dont(nav_service):
    instance = make_view(
        ProductView,
        nav_service=nav_service,
        path_params={"id": "1"},
        query={"tab": "stock"},
    )
    assert instance.params.tab == "stock"


def test_invalid_param_raises_validation_error(nav_service):
    with pytest.raises(ValidationError):
        make_view(ProductView, nav_service=nav_service, path_params={"id": "not_a_number"})


# ── Content coercion ───────────────────────────────────────────────────────

def test_content_can_be_a_list_and_gets_wrapped(nav_service):
    class ListContent(HelloView):
        def build_content(self):
            return [ft.Text("a"), ft.Text("b")]

    v = make_view(ListContent, nav_service=nav_service).render()
    # No exception means the list was wrapped successfully into a Column.
    assert v.controls
