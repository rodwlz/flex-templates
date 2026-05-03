"""
Pong view — wires an adapter to the engine and renders state.

Swap one line to change the driver:
    adapter = KeyboardAdapter()       # human control
    adapter = MockNeuralAdapter()     # AI control

That single line is the entire LEGO proof — engine and view never change.

Run with:  flet run games/view.py
"""
from __future__ import annotations

import asyncio
import flet as ft

from games.contracts import PongState
from games.engine import PongEngine
from games.keyboard_adapter import KeyboardAdapter
from games.mock_neural_adapter import MockNeuralAdapter  # noqa: F401 — swap-in alternative


def _rect(left, top, width, height, color="white") -> ft.Container:
    return ft.Container(
        left=left, top=top, width=width, height=height,
        bgcolor=color, border_radius=2,
    )


def _render(stack: ft.Stack, state: PongState) -> None:
    stack.controls = [
        _rect(0, state.left_y, state.paddle_w, state.paddle_h),
        _rect(state.width - state.paddle_w, state.right_y, state.paddle_w, state.paddle_h),
        _rect(state.ball_x, state.ball_y, state.ball_size, state.ball_size, color="yellow"),
        ft.Text(
            f"{state.left_score}   {state.right_score}",
            size=28, color="white",
            top=10, left=state.width / 2 - 40,
        ),
    ]


def main(page: ft.Page):
    page.title = "Pong — LEGO demo"
    page.bgcolor = "black"
    page.padding = 0

    state = PongState()
    engine = PongEngine(state)

    # ── Swap this line to switch drivers ───────────────────────────────────
    adapter = KeyboardAdapter()
    # adapter = MockNeuralAdapter()

    stack = ft.Stack(width=state.width, height=state.height)
    page.add(stack)
    page.on_keyboard_event = getattr(adapter, "on_key", lambda e: None)

    async def loop():
        while True:
            inp = adapter.get_input(engine.state)
            new_state = engine.step(inp)
            _render(stack, new_state)
            page.update()
            await asyncio.sleep(1 / 60)

    page.run_task(loop)


if __name__ == "__main__":
    ft.app(target=main)
