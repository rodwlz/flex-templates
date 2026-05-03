from collections import defaultdict
from typing import Callable
from lib.contracts.base import Event


class Events:
    """Thin wrapper around EventBus with a clean on/off/emit API.

    Usage in views / services (events is in props):
        self.events.on("user.created", self._on_user_created)
        self.events.emit("order.placed", {"order_id": 42})
        self.events.off("user.created", self._on_user_created)
    """

    def __init__(self, bus: "EventBus"):
        self._bus = bus

    def on(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Subscribe *callback* to *event_type*."""
        self._bus.subscribe(event_type, callback)

    def off(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Unsubscribe *callback* from *event_type*."""
        self._bus.unsubscribe(event_type, callback)

    def emit(self, event_type: str, payload: dict | None = None) -> None:
        """Publish an event of *event_type* with optional *payload*."""
        self._bus.publish(Event(type=event_type, payload=payload or {}))


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        for callback in self._subscribers.get(event.type, []):
            try:
                callback(event)
            except Exception as exc:
                import sys
                print(f"[EventBus] subscriber error on {event.type!r}: {exc}", file=sys.stderr)
