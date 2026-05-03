"""EventBus: simple publish/subscribe. Don't break the wires."""
from lib.contracts.base import Event


def test_subscriber_receives_published_event(event_bus):
    received = []
    event_bus.subscribe("ping", lambda e: received.append(e))

    event_bus.publish(Event(type="ping", payload={"n": 1}))

    assert len(received) == 1
    assert received[0].payload["n"] == 1


def test_multiple_subscribers_all_fire(event_bus):
    a, b = [], []
    event_bus.subscribe("ping", lambda e: a.append(e))
    event_bus.subscribe("ping", lambda e: b.append(e))

    event_bus.publish(Event(type="ping"))

    assert len(a) == 1
    assert len(b) == 1


def test_event_with_no_subscribers_does_not_crash(event_bus):
    # Nothing subscribed — should silently no-op, not blow up.
    event_bus.publish(Event(type="nobody.listening"))


def test_unsubscribe_stops_callbacks(event_bus):
    received = []

    def listener(e):
        received.append(e)

    event_bus.subscribe("ping", listener)
    event_bus.unsubscribe("ping", listener)

    event_bus.publish(Event(type="ping"))

    assert received == []


def test_unsubscribe_unknown_callback_is_safe(event_bus):
    # Calling unsubscribe on something never subscribed must not crash.
    event_bus.unsubscribe("ping", lambda e: None)


def test_subscribers_only_receive_their_event_type(event_bus):
    pings, pongs = [], []
    event_bus.subscribe("ping", lambda e: pings.append(e))
    event_bus.subscribe("pong", lambda e: pongs.append(e))

    event_bus.publish(Event(type="ping"))

    assert len(pings) == 1
    assert len(pongs) == 0
