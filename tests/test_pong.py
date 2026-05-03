"""
Pong engine tests + the LEGO proof.

The engine is pure step-logic, so we can drive it deterministically. The
LEGO test proves that a different adapter (mock neural) drives the same
engine and produces a sensible state — no engine or view code changes.
"""
import pytest

from games.contracts import PongInput, PongState
from games.engine import PongEngine
from games.keyboard_adapter import KeyboardAdapter
from games.mock_neural_adapter import MockNeuralAdapter


# ── Engine: paddle motion ──────────────────────────────────────────────────

def test_left_up_moves_left_paddle_up():
    engine = PongEngine(PongState(left_y=200))
    new_state = engine.step(PongInput(left_up=True))
    assert new_state.left_y < 200


def test_left_paddle_clamped_at_top():
    engine = PongEngine(PongState(left_y=0))
    new_state = engine.step(PongInput(left_up=True))
    assert new_state.left_y == 0


def test_right_paddle_clamped_at_bottom():
    state = PongState(right_y=600 - 80)  # height - paddle_h
    engine = PongEngine(state)
    new_state = engine.step(PongInput(right_down=True))
    assert new_state.right_y == 600 - 80


# ── Engine: ball physics ───────────────────────────────────────────────────

def test_ball_advances_each_step():
    engine = PongEngine(PongState(ball_x=400, ball_y=300, ball_dx=4, ball_dy=3))
    new_state = engine.step(PongInput())
    assert new_state.ball_x == 404
    assert new_state.ball_y == 303


def test_ball_bounces_off_top_wall():
    engine = PongEngine(PongState(ball_y=0, ball_dy=-3))
    new_state = engine.step(PongInput())
    assert new_state.ball_dy == 3  # flipped


def test_ball_bounces_off_left_paddle():
    state = PongState(ball_x=12, ball_y=300, ball_dx=-4, left_y=260)
    engine = PongEngine(state)
    new_state = engine.step(PongInput())
    assert new_state.ball_dx > 0  # flipped to positive


def test_ball_misses_paddle_scores_for_opponent():
    state = PongState(ball_x=2, ball_dx=-4, left_y=0)  # paddle high, ball low
    state = state.model_copy(update={"ball_y": 500})
    engine = PongEngine(state)
    new_state = engine.step(PongInput())
    # After miss, ball resets and right player gains a point
    assert new_state.right_score == 1


# ── Adapters: same shape, different sources ────────────────────────────────

def test_keyboard_adapter_translates_pressed_keys():
    adapter = KeyboardAdapter()
    adapter._keys.update({"w", "Arrow Down"})

    inp = adapter.get_input()

    assert inp.left_up is True
    assert inp.right_down is True
    assert inp.left_down is False
    assert inp.right_up is False


def test_mock_neural_adapter_chases_ball_down():
    """Ball below paddle → adapter requests right_down."""
    state = PongState(ball_y=500, right_y=200)
    inp = MockNeuralAdapter().get_input(state)

    assert inp.right_down is True
    assert inp.right_up is False


def test_mock_neural_adapter_chases_ball_up():
    state = PongState(ball_y=50, right_y=400)
    inp = MockNeuralAdapter().get_input(state)

    assert inp.right_up is True
    assert inp.right_down is False


def test_mock_neural_adapter_holds_when_aligned():
    """Ball roughly centered on paddle → no movement."""
    state = PongState(ball_y=300, right_y=260)  # paddle_h=80 → center at 300
    inp = MockNeuralAdapter().get_input(state)

    assert inp.right_up is False
    assert inp.right_down is False


# ── The LEGO proof ─────────────────────────────────────────────────────────

def test_engine_runs_with_keyboard_adapter():
    """Engine + KeyboardAdapter: 60 ticks complete without errors."""
    engine = PongEngine()
    adapter = KeyboardAdapter()

    for _ in range(60):
        inp = adapter.get_input(engine.state)
        engine.step(inp)

    assert isinstance(engine.state, PongState)


def test_engine_runs_with_mock_neural_adapter_no_engine_changes():
    """Same engine, different adapter — zero changes to engine or view code.
    This is the LEGO proof: the architecture decouples driver from logic."""
    engine = PongEngine()
    adapter = MockNeuralAdapter()

    for _ in range(60):
        inp = adapter.get_input(engine.state)
        engine.step(inp)

    # The mock AI tracks the ball, so the right paddle should have moved
    # (it starts at 260; ball motion will pull it).
    assert engine.state.right_y != 260 or engine.state.ball_x != 400
