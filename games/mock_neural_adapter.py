"""
MockNeuralAdapter — pretends to be a neural net that tracks the ball.

Same get_input(state) signature as KeyboardAdapter. Swapping
`KeyboardAdapter()` for `MockNeuralAdapter()` in the view is the only
change needed to switch from human to AI control. That's the LEGO proof.

A real neural net (PyTorch/TF) would replace the rule-based logic in
get_input() with model.predict(state) — same interface either way.
"""
from __future__ import annotations

from games.contracts import PongInput, PongState


class MockNeuralAdapter:
    def __init__(self, dead_zone: int = 20):
        self._dead_zone = dead_zone

    def get_input(self, state: PongState | None = None) -> PongInput:
        if state is None:
            return PongInput()

        paddle_center = state.right_y + state.paddle_h / 2
        ball_center = state.ball_y + state.ball_size / 2
        diff = ball_center - paddle_center

        return PongInput(
            right_up=diff < -self._dead_zone,
            right_down=diff > self._dead_zone,
        )
