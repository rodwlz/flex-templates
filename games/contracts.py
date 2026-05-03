"""
The plugs for the Pong LEGO demo.

PongInput is what every adapter (keyboard, neural net, replay file)
produces. PongEngine consumes it. PongState is what the engine produces
and the view renders. Engine never imports from `lib` — proving the
architecture works without framework coupling.
"""
from __future__ import annotations

from pydantic import BaseModel


class PongInput(BaseModel):
    left_up: bool = False
    left_down: bool = False
    right_up: bool = False
    right_down: bool = False


class PongState(BaseModel):
    ball_x: float = 400.0
    ball_y: float = 300.0
    ball_dx: float = 4.0
    ball_dy: float = 3.0

    left_y: float = 260.0
    right_y: float = 260.0

    left_score: int = 0
    right_score: int = 0

    width: int = 800
    height: int = 600
    paddle_w: int = 12
    paddle_h: int = 80
    ball_size: int = 12
