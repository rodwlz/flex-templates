"""
PongEngine — pure step logic, zero framework imports.

step(input) → next state. That's it. No Flet, no DB, no event bus.
This is the heart of the LEGO proof: any adapter that produces PongInput
can drive this engine, and any view that reads PongState can render it.
"""
from __future__ import annotations

from games.contracts import PongInput, PongState


class PongEngine:
    PADDLE_SPEED = 7.0

    def __init__(self, state: PongState | None = None):
        self._state = state or PongState()

    @property
    def state(self) -> PongState:
        return self._state

    def step(self, inp: PongInput) -> PongState:
        s = self._state
        s = self._move_paddles(s, inp)
        s = self._move_ball(s)
        self._state = s
        return s

    def _move_paddles(self, s: PongState, inp: PongInput) -> PongState:
        max_y = float(s.height - s.paddle_h)
        left_y = s.left_y
        right_y = s.right_y

        if inp.left_up:
            left_y = max(0.0, left_y - self.PADDLE_SPEED)
        if inp.left_down:
            left_y = min(max_y, left_y + self.PADDLE_SPEED)
        if inp.right_up:
            right_y = max(0.0, right_y - self.PADDLE_SPEED)
        if inp.right_down:
            right_y = min(max_y, right_y + self.PADDLE_SPEED)

        return s.model_copy(update={"left_y": left_y, "right_y": right_y})

    def _move_ball(self, s: PongState) -> PongState:
        ball_x = s.ball_x + s.ball_dx
        ball_y = s.ball_y + s.ball_dy
        ball_dx = s.ball_dx
        ball_dy = s.ball_dy
        left_score = s.left_score
        right_score = s.right_score

        # Top/bottom walls
        if ball_y <= 0 or ball_y + s.ball_size >= s.height:
            ball_dy = -ball_dy
            ball_y = max(0.0, min(float(s.height - s.ball_size), ball_y))

        # Left paddle
        if (
            ball_dx < 0
            and ball_x <= s.paddle_w
            and s.left_y <= ball_y + s.ball_size
            and ball_y <= s.left_y + s.paddle_h
        ):
            ball_dx = -ball_dx
            ball_x = float(s.paddle_w)

        # Right paddle
        right_edge = s.width - s.paddle_w - s.ball_size
        if (
            ball_dx > 0
            and ball_x >= right_edge
            and s.right_y <= ball_y + s.ball_size
            and ball_y <= s.right_y + s.paddle_h
        ):
            ball_dx = -ball_dx
            ball_x = float(right_edge)

        # Scoring (ball leaves the playfield horizontally)
        if ball_x < 0:
            right_score += 1
            ball_x, ball_y = float(s.width / 2), float(s.height / 2)
            ball_dx = abs(s.ball_dx)
            ball_dy = s.ball_dy
        elif ball_x > s.width:
            left_score += 1
            ball_x, ball_y = float(s.width / 2), float(s.height / 2)
            ball_dx = -abs(s.ball_dx)
            ball_dy = s.ball_dy

        return s.model_copy(update={
            "ball_x": ball_x,
            "ball_y": ball_y,
            "ball_dx": ball_dx,
            "ball_dy": ball_dy,
            "left_score": left_score,
            "right_score": right_score,
        })
