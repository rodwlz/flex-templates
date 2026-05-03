"""NavigationService: browser-like history. No Flet involved."""
from lib.contracts.base import ActionRequest, Event


def visit(nav, url):
    return nav.execute(ActionRequest(action="visit", data={"url": url}))


def back(nav):
    return nav.execute(ActionRequest(action="back"))


def forward(nav):
    return nav.execute(ActionRequest(action="forward"))


def test_starts_on_homepage(nav_service):
    assert nav_service.current == "/"
    assert nav_service.can_go_back is False
    assert nav_service.can_go_forward is False


def test_visit_changes_current_url(nav_service):
    visit(nav_service, "/login")
    assert nav_service.current == "/login"


def test_visit_makes_back_available(nav_service):
    visit(nav_service, "/login")
    assert nav_service.can_go_back is True


def test_visit_publishes_route_changed_event(nav_service, event_bus):
    received = []
    event_bus.subscribe("nav.route_changed", lambda e: received.append(e))

    visit(nav_service, "/products")

    assert len(received) == 1
    assert received[0].payload["url"] == "/products"


def test_visiting_same_url_is_a_noop(nav_service, event_bus):
    received = []
    event_bus.subscribe("nav.route_changed", lambda e: received.append(e))

    visit(nav_service, "/")  # already at "/"

    assert received == []
    assert nav_service.can_go_back is False


def test_back_returns_to_previous_url(nav_service):
    visit(nav_service, "/login")
    visit(nav_service, "/products")

    back(nav_service)

    assert nav_service.current == "/login"


def test_forward_redoes_a_back(nav_service):
    visit(nav_service, "/login")
    back(nav_service)
    forward(nav_service)
    assert nav_service.current == "/login"


def test_back_at_homepage_returns_failure(nav_service):
    result = back(nav_service)
    assert result.success is False
    assert "previous" in result.error.lower()


def test_forward_with_no_forward_stack_returns_failure(nav_service):
    result = forward(nav_service)
    assert result.success is False


def test_new_visit_clears_forward_stack(nav_service):
    visit(nav_service, "/login")
    back(nav_service)
    visit(nav_service, "/products")  # this should wipe forward history

    assert nav_service.can_go_forward is False


def test_unknown_action_returns_error(nav_service):
    result = nav_service.execute(ActionRequest(action="teleport"))
    assert result.success is False
    assert "Unknown action" in result.error


# ── New jump/peek/clear features ──────────────────────────────────────────


def test_back_with_steps_jumps_multiple_pages(nav_service):
    visit(nav_service, "/a")
    visit(nav_service, "/b")
    visit(nav_service, "/c")

    nav_service.execute(ActionRequest(action="back", data={"steps": 2}))

    assert nav_service.current == "/a"
    assert nav_service.can_go_forward is True


def test_forward_with_steps_jumps_multiple_pages(nav_service):
    visit(nav_service, "/a")
    visit(nav_service, "/b")
    visit(nav_service, "/c")
    nav_service.execute(ActionRequest(action="back", data={"steps": 3}))

    nav_service.execute(ActionRequest(action="forward", data={"steps": 2}))

    assert nav_service.current == "/b"


def test_back_steps_clamps_to_history_length(nav_service):
    visit(nav_service, "/a")
    visit(nav_service, "/b")

    nav_service.execute(ActionRequest(action="back", data={"steps": 99}))

    assert nav_service.current == "/"  # clamped, not crashed


def test_peek_prev_shows_previous_url_without_navigating(nav_service):
    visit(nav_service, "/login")
    visit(nav_service, "/products")

    assert nav_service.peek_prev == "/login"
    assert nav_service.current == "/products"  # didn't move


def test_peek_next_shows_next_url_without_navigating(nav_service):
    visit(nav_service, "/login")
    back(nav_service)

    assert nav_service.peek_next == "/login"
    assert nav_service.current == "/"


def test_peek_prev_is_none_at_homepage(nav_service):
    assert nav_service.peek_prev is None


def test_peek_next_is_none_with_empty_forward_stack(nav_service):
    assert nav_service.peek_next is None


def test_clear_resets_history_keeping_current(nav_service):
    visit(nav_service, "/a")
    visit(nav_service, "/b")

    nav_service.execute(ActionRequest(action="clear"))

    assert nav_service.current == "/b"
    assert nav_service.can_go_back is False
    assert nav_service.can_go_forward is False


def test_back_stack_property_is_a_copy(nav_service):
    visit(nav_service, "/a")
    snapshot = nav_service.back_stack
    snapshot.append("/tampered")

    assert "/tampered" not in nav_service.back_stack


def test_nav_state_includes_full_stacks_and_peeks(nav_service):
    visit(nav_service, "/a")
    visit(nav_service, "/b")
    back(nav_service)

    state = nav_service.execute(ActionRequest(action="current")).data

    assert state["url"] == "/a"
    assert state["prev"] == "/"
    assert state["next"] == "/b"
    assert state["back_stack"] == ["/", "/a"]
    assert state["forward_stack"] == ["/b"]
