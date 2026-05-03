from lib.contracts.base import ActionRequest, ActionResult, Event
from lib.core.events import EventBus
from lib.core.interfaces import IService


class NavigationService(IService):
    """
    Browser-like navigation history with back/forward stacks.
    Publishes nav.route_changed events — no Flet imports here.

    Actions:
        visit   data={"url": "/page"}                → push a new URL
        back    data={"steps": 1}                    → go back N (default 1)
        forward data={"steps": 1}                    → go forward N (default 1)
        clear                                        → reset to current page only
        current                                      → read state without changes
    """

    def __init__(self, event_bus: EventBus, homepage: str = "/"):
        self._event_bus = event_bus
        self._back_stack: list[str] = [homepage]
        self._forward_stack: list[str] = []

    # ── Public contract interface ──────────────────────────────────────────

    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "visit":
                return self._visit(request.data.get("url", "/"))
            case "back":
                return self._back(int(request.data.get("steps", 1)))
            case "forward":
                return self._forward(int(request.data.get("steps", 1)))
            case "clear":
                return self._clear()
            case "current":
                return ActionResult(success=True, data=self._nav_state())
            case _:
                return ActionResult(success=False, error=f"Unknown action: {request.action}")

    # ── Read-only properties ───────────────────────────────────────────────

    @property
    def current(self) -> str:
        return self._back_stack[-1]

    @property
    def can_go_back(self) -> bool:
        return len(self._back_stack) > 1

    @property
    def can_go_forward(self) -> bool:
        return bool(self._forward_stack)

    @property
    def peek_prev(self) -> str | None:
        return self._back_stack[-2] if self.can_go_back else None

    @property
    def peek_next(self) -> str | None:
        return self._forward_stack[-1] if self.can_go_forward else None

    @property
    def back_stack(self) -> list[str]:
        return list(self._back_stack)

    @property
    def forward_stack(self) -> list[str]:
        return list(reversed(self._forward_stack))

    # ── Private actions ────────────────────────────────────────────────────

    def _visit(self, url: str) -> ActionResult:
        if url == self.current:
            return ActionResult(success=True, data=self._nav_state())

        self._back_stack.append(url)
        self._forward_stack.clear()

        return self._emit_and_return(url)

    def _back(self, steps: int) -> ActionResult:
        if not self.can_go_back or steps < 1:
            return ActionResult(success=False, error="No previous page")

        steps = min(steps, len(self._back_stack) - 1)
        for _ in range(steps):
            self._forward_stack.append(self._back_stack.pop())
        return self._emit_and_return(self.current)

    def _forward(self, steps: int) -> ActionResult:
        if not self.can_go_forward or steps < 1:
            return ActionResult(success=False, error="No next page")

        steps = min(steps, len(self._forward_stack))
        for _ in range(steps):
            self._back_stack.append(self._forward_stack.pop())
        return self._emit_and_return(self.current)

    def _clear(self) -> ActionResult:
        self._back_stack = [self.current]
        self._forward_stack.clear()
        return ActionResult(success=True, data=self._nav_state())

    def _emit_and_return(self, url: str) -> ActionResult:
        event = Event(type="nav.route_changed", payload=self._nav_state())
        self._event_bus.publish(event)
        return ActionResult(success=True, data=self._nav_state(), events=[event])

    def _nav_state(self) -> dict:
        return {
            "url": self.current,
            "can_go_back": self.can_go_back,
            "can_go_forward": self.can_go_forward,
            "prev": self.peek_prev,
            "next": self.peek_next,
            "back_stack": self.back_stack,
            "forward_stack": self.forward_stack,
        }
