"""FletRouter: URL → view. Convention routing, named routes, query strings."""
from tests.conftest import FakePage


def render(router, url):
    page = FakePage(url)
    router.route_change(page)
    return page


def test_root_url_loads_home_view(router):
    page = render(router, "/")
    assert len(page.views) == 1


def test_known_url_loads_matching_view(router):
    page = render(router, "/login")
    assert len(page.views) == 1


def test_unknown_url_falls_back_to_not_found(router):
    page = render(router, "/this-does-not-exist")
    assert len(page.views) == 1  # 404 view rendered, not a crash


def test_page_update_is_called_after_route_change(router):
    page = render(router, "/")
    assert page.update_count == 1


def test_views_are_cleared_before_new_view_is_appended(router):
    page = FakePage("/")
    page.views.append("OLD VIEW")  # something stale
    router.route_change(page)

    assert "OLD VIEW" not in page.views


def test_named_route_captures_path_params(router):
    """When you register /products/{id}, visiting /products/42 sets params['id'] = '42'."""
    captured = {}

    def fake_view(page, props):
        captured["params"] = props["params"]
        captured["query"] = props["query"]
        # Return a real ft.View shape so router doesn't choke
        import flet as ft
        return ft.View(route="/products/42", controls=[ft.Text("ok")])

    # Inject a fake module so we don't need a real file
    import types
    mod = types.ModuleType("fake_product_detail")
    mod.view = fake_view
    router._cache["fake_product_detail"] = mod
    router.register("/products/{id}", "fake_product_detail")

    render(router, "/products/42")

    assert captured["params"] == {"id": "42"}


def test_query_strings_land_in_props_query(router):
    captured = {}

    def fake_view(page, props):
        captured["query"] = props["query"]
        import flet as ft
        return ft.View(route="/", controls=[])

    import types
    mod = types.ModuleType("fake_home")
    mod.view = fake_view
    router._cache["lib.views.home"] = mod  # override the home view

    render(router, "/?tab=stock&sort=name")

    assert captured["query"] == {"tab": "stock", "sort": "name"}


def test_modules_are_cached_after_first_load(router):
    render(router, "/")
    assert "lib.views.home" in router._cache


def test_invalidate_cache_clears_specific_module(router):
    render(router, "/")
    router.invalidate_cache("lib.views.home")
    assert "lib.views.home" not in router._cache


def test_invalidate_cache_with_no_arg_clears_everything(router):
    render(router, "/")
    render(router, "/login")
    router.invalidate_cache()
    assert router._cache == {}
