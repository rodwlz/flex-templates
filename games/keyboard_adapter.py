"""
KeyboardAdapter — Flet key events → PongInput.

Bind on_keyboard_event to .on_key. The view calls .get_input() each tick.
"""
from __future__ import annotations

from games.contracts import PongInput, PongState


class KeyboardAdapter:
    def __init__(self):
        self._keys: set[str] = set()

    def on_key(self, e) -> None:
        """Wire to page.on_keyboard_event. Tracks press/release as a key set."""
        # Flet's KeyboardEvent doesn't distinguish press/release on every platform,
        # so we treat each event as "pressed" and clear stale keys after each tick
        # via clear_held() if the host wants release semantics.
        self._keys.add(e.key)

    def clear_held(self) -> None:
        """Optional: call after each tick if your platform doesn't emit key-up."""
        self._keys.clear()

    def get_input(self, state: PongState | None = None) -> PongInput:
        return PongInput(
            left_up="W" in self._keys or "w" in self._keys,
            left_down="S" in self._keys or "s" in self._keys,
            right_up="Arrow Up" in self._keys,
            right_down="Arrow Down" in self._keys,
        )
