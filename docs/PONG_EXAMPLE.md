# FlexTemplates 2.0 — Complete Pong Example

## Why Pong?

Pong is a perfect example of the LEGO architecture because it can be driven by three different "input sources":

1. **Keyboard** — a human pressing arrow keys in a Flet window
2. **API** — an external program sending HTTP requests
3. **Neural Net** — a trained RL agent deciding moves automatically

The game engine is identical in all three cases. Only the **input adapter** changes. This is the LEGO plug in action.

---

## Step 1: Define the Contracts (The Plugs)

The contracts define what data flows in and out of the engine. Write these first.

```python
# games/contracts.py

from pydantic import BaseModel

class PongInput(BaseModel):
    """What you send INTO the engine each frame."""
    action: str  # "move_up", "move_down", or "idle"

class PongState(BaseModel):
    """What the engine sends BACK after each frame."""
    ball_x: float
    ball_y: float
    ball_vx: float  # velocity x
    ball_vy: float  # velocity y
    paddle_y: float
    score_left: int
    score_right: int
    game_over: bool = False
    winner: str | None = None  # "left" or "right"
```

**Why these two?**

- `PongInput` is the "request" — what the controller wants to happen
- `PongState` is the "result" — what the game looks like after the step

Anyone can drive the engine as long as they produce a `PongInput`. Anyone can render the game as long as they understand `PongState`.

---

## Step 2: Build the Pure Engine

The engine is pure game logic. **No Flet, no FastAPI, no neural nets.** It only knows about `PongInput` and `PongState`.

```python
# games/engine.py

from games.contracts import PongInput, PongState

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
PADDLE_HEIGHT = 50
BALL_SIZE = 10

class PongEngine:
    def __init__(self):
        self.state = PongState(
            ball_x=CANVAS_WIDTH / 2,
            ball_y=CANVAS_HEIGHT / 2,
            ball_vx=5.0,
            ball_vy=3.0,
            paddle_y=CANVAS_HEIGHT / 2 - PADDLE_HEIGHT / 2,
            score_left=0,
            score_right=0,
        )
    
    def step(self, input: PongInput) -> PongState:
        """Advance the game by one frame given the player's input."""
        self._move_paddle(input.action)
        self._move_ball()
        self._check_collisions()
        self._check_scoring()
        return self.state
    
    def _move_paddle(self, action: str):
        if action == "move_up":
            self.state.paddle_y = max(0, self.state.paddle_y - 10)
        elif action == "move_down":
            self.state.paddle_y = min(
                CANVAS_HEIGHT - PADDLE_HEIGHT, 
                self.state.paddle_y + 10
            )
    
    def _move_ball(self):
        self.state.ball_x += self.state.ball_vx
        self.state.ball_y += self.state.ball_vy
    
    def _check_collisions(self):
        # Bounce off top/bottom walls
        if self.state.ball_y <= 0 or self.state.ball_y >= CANVAS_HEIGHT:
            self.state.ball_vy *= -1
        
        # Bounce off right-side paddle (AI paddle, always centered for simplicity)
        if (self.state.ball_x >= CANVAS_WIDTH - 20 and
            abs(self.state.ball_y - CANVAS_HEIGHT / 2) < PADDLE_HEIGHT):
            self.state.ball_vx *= -1
        
        # Bounce off left-side paddle (player paddle)
        if (self.state.ball_x <= 20 and
            abs(self.state.ball_y - self.state.paddle_y) < PADDLE_HEIGHT):
            self.state.ball_vx *= -1
    
    def _check_scoring(self):
        if self.state.ball_x <= 0:
            # Right player scores
            self.state.score_right += 1
            self._reset_ball()
        elif self.state.ball_x >= CANVAS_WIDTH:
            # Left player scores
            self.state.score_left += 1
            self._reset_ball()
    
    def _reset_ball(self):
        self.state.ball_x = CANVAS_WIDTH / 2
        self.state.ball_y = CANVAS_HEIGHT / 2
        self.state.ball_vx *= -1  # serve to other side
```

**Notice:** This class has zero imports from Flet, FastAPI, or any neural network library. It only uses the contracts defined in `games/contracts.py`.

---

## Step 3: Write the Keyboard Adapter (Flet Input)

The keyboard adapter translates Flet keyboard events into `PongInput` contracts.

```python
# games/keyboard_adapter.py

import flet as ft
from games.contracts import PongInput
from games.engine import PongEngine

class KeyboardAdapter:
    """Translates Flet keyboard events into PongInput contracts."""
    
    def __init__(self, engine: PongEngine, on_state_update):
        self.engine = engine
        self.on_state_update = on_state_update  # callback to re-render
        self._current_action = "idle"
    
    def on_key_down(self, e: ft.KeyboardEvent):
        """Called by Flet when a key is pressed."""
        if e.key == "Arrow Up":
            self._current_action = "move_up"
        elif e.key == "Arrow Down":
            self._current_action = "move_down"
        
        # Step the engine with current action
        self._step()
    
    def on_key_up(self, e: ft.KeyboardEvent):
        """Called by Flet when a key is released."""
        self._current_action = "idle"
    
    def _step(self):
        # Translate current key state to contract
        input = PongInput(action=self._current_action)
        
        # Step the engine — pure logic, no Flet
        state = self.engine.step(input)
        
        # Notify the view to re-render
        self.on_state_update(state)
```

**Key points:**
- `KeyboardAdapter` knows about Flet (it receives `ft.KeyboardEvent`)
- `PongEngine` knows nothing about Flet — it only sees `PongInput`
- The adapter is the bridge between the two worlds

---

## Step 4: Write the Neural Net Adapter

The neural net adapter translates model output into `PongInput` contracts.

```python
# games/neural_adapter.py

from games.contracts import PongInput, PongState
from games.engine import PongEngine

class NeuralAdapter:
    """Translates neural network output into PongInput contracts."""
    
    def __init__(self, engine: PongEngine, model):
        self.engine = engine
        self.model = model
        self.action_map = ["move_up", "move_down", "idle"]
    
    def step(self, observation) -> PongState:
        """Run one frame of the game using the model's decision."""
        # Model predicts action probabilities
        # e.g. [0.1, 0.8, 0.1] → model wants "move_down"
        raw_output = self.model.predict(observation)
        
        # Translate to contract
        action_index = raw_output.argmax()
        action = self.action_map[action_index]
        input = PongInput(action=action)
        
        # Step the engine — IDENTICAL to keyboard adapter from here
        state = self.engine.step(input)
        
        return state
    
    def get_observation(self) -> list[float]:
        """Extract numeric observation from game state (for RL training)."""
        state = self.engine.state
        return [
            state.ball_x / 800,      # normalize to 0-1
            state.ball_y / 600,
            state.ball_vx / 10,
            state.ball_vy / 10,
            state.paddle_y / 600,
        ]
```

**Notice:** From `engine.step(input)` onward, this code is identical to the keyboard adapter. The engine doesn't know or care who is calling it.

---

## Step 5: Wrap in a Service (ActionRequest / ActionResult)

If you want to expose Pong over an API, wrap it in a service:

```python
# games/pong_service.py

from flex_app.contracts.base import ActionRequest, ActionResult
from flex_app.core.interfaces import IService
from games.contracts import PongInput
from games.engine import PongEngine

class PongService(IService):
    """Wraps PongEngine in the FlexTemplates contract system."""
    
    def __init__(self):
        self.engine = PongEngine()
    
    def execute(self, request: ActionRequest) -> ActionResult:
        if request.action == "step":
            return self._step(request.data)
        if request.action == "reset":
            return self._reset()
        return ActionResult(success=False, error=f"Unknown action: {request.action}")
    
    def _step(self, data: dict) -> ActionResult:
        action = data.get("action", "idle")
        if action not in ("move_up", "move_down", "idle"):
            return ActionResult(success=False, error=f"Invalid action: {action}")
        
        input = PongInput(action=action)
        state = self.engine.step(input)
        
        return ActionResult(
            success=True,
            data=state.model_dump()
        )
    
    def _reset(self) -> ActionResult:
        self.engine = PongEngine()
        return ActionResult(success=True, data=self.engine.state.model_dump())
```

---

## Step 6: Expose via API Endpoint

```python
# api/routes/pong.py

from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from flex_app.container import Container
from flex_app.contracts.base import ActionRequest

router = APIRouter(prefix="/pong")

@router.post("/step")
@inject
async def pong_step(
    action: str,
    service = Depends(Provide[Container.pong_service])
):
    """Advance the game by one frame. action: move_up | move_down | idle"""
    result = service.execute(ActionRequest(
        action="step",
        data={"action": action}
    ))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data

@router.post("/reset")
@inject
async def pong_reset(
    service = Depends(Provide[Container.pong_service])
):
    """Reset the game to initial state."""
    result = service.execute(ActionRequest(action="reset"))
    return result.data
```

---

## Step 7: Use in a Training Loop (RL Agent)

```python
# games/train.py

from games.engine import PongEngine
from games.neural_adapter import NeuralAdapter
from my_rl_library import PPOAgent  # your RL library of choice

def train(episodes: int = 1000):
    engine = PongEngine()
    model = PPOAgent(obs_size=5, action_size=3)
    adapter = NeuralAdapter(engine=engine, model=model)
    
    for episode in range(episodes):
        # Reset game
        engine = PongEngine()
        adapter.engine = engine
        
        done = False
        total_reward = 0
        
        while not done:
            # Get observation
            obs = adapter.get_observation()
            
            # Step the game (model decides action)
            state = adapter.step(obs)
            
            # Calculate reward
            reward = state.score_left - state.score_right
            total_reward += reward
            
            # Check if game is over
            done = state.game_over
        
        # Train model on collected experience
        model.update()
        
        if episode % 100 == 0:
            print(f"Episode {episode}: total_reward={total_reward}")
```

**Notice:** The training loop doesn't touch Flet at all. The engine, adapter, and training code are completely decoupled from the UI.

---

## The Full Data Flow (Visual)

```
KEYBOARD INPUT:
─────────────────────────────────────────────────────
Flet KeyEvent("Arrow Up")
  → KeyboardAdapter.on_key_down(e)
      → PongInput(action="move_up")
          → PongEngine.step(input)
              → PongState(ball_x=..., paddle_y=...)
          → on_state_update(state)
              → PongView.render(state)
                  → page.update()

NEURAL NET INPUT:
─────────────────────────────────────────────────────
observation = [0.5, 0.3, 0.6, -0.2, 0.4]
  → NeuralAdapter.step(observation)
      → model.predict(obs) → [0.1, 0.8, 0.1]
          → PongInput(action="move_down")
              → PongEngine.step(input)    ← SAME CODE FROM HERE
                  → PongState(ball_x=..., paddle_y=...)

API INPUT:
─────────────────────────────────────────────────────
POST /pong/step { "action": "move_up" }
  → pong_step(action="move_up")
      → PongService.execute(ActionRequest(action="step", data={"action": "move_up"}))
          → PongInput(action="move_up")
              → PongEngine.step(input)    ← SAME CODE FROM HERE
                  → PongState(...)
              → ActionResult(success=True, data={...})
          → JSON response
```

**The engine runs the same code every time.** Only the source of `PongInput` changes.

---

## Why This Architecture Is Powerful

### Scenario 1: You want to add a web frontend

You have the keyboard adapter for the Flet UI. Now you want a web interface too.

**With contracts:** Add a new endpoint that calls the same `PongService`. Done. The engine doesn't change.

**Without contracts:** You'd have to extract game logic from your UI code, dealing with tight coupling everywhere.

### Scenario 2: You want to train an RL agent

You have the game running in Flet. You want to train a neural net to play.

**With contracts:** The `NeuralAdapter` drives the same engine using the same `PongInput` contract. The engine doesn't know it's being trained.

**Without contracts:** Your training loop would need access to internal Flet state. You'd have two separate game implementations.

### Scenario 3: You want to replay games

You want to record games and replay them later.

**With contracts:** Record the sequence of `PongInput` contracts. Replay by feeding them back into the engine.

**Without contracts:** You'd have to serialize internal state, which is a mess.

---

## Complete File Structure for Pong Demo

```
games/
├── contracts.py          # PongInput, PongState
├── engine.py             # PongEngine (pure logic, no UI)
├── keyboard_adapter.py   # Flet key events → PongInput
├── neural_adapter.py     # NN output → PongInput
├── pong_service.py       # ActionRequest/Result wrapper
├── view.py               # Flet canvas renders PongState
└── train.py              # RL training loop
```

Each file does one thing. The engine is the heart. The adapters are the plugs. The view is the screen.

---

## Testing Pong (No Flet Needed)

Because the engine is pure logic, you can test it without starting a Flet app:

```python
# tests/test_pong_engine.py

from games.engine import PongEngine
from games.contracts import PongInput

def test_paddle_moves_up():
    engine = PongEngine()
    initial_y = engine.state.paddle_y
    
    state = engine.step(PongInput(action="move_up"))
    
    assert state.paddle_y < initial_y

def test_paddle_moves_down():
    engine = PongEngine()
    initial_y = engine.state.paddle_y
    
    state = engine.step(PongInput(action="move_down"))
    
    assert state.paddle_y > initial_y

def test_idle_keeps_paddle():
    engine = PongEngine()
    initial_y = engine.state.paddle_y
    
    state = engine.step(PongInput(action="idle"))
    
    assert state.paddle_y == initial_y

def test_ball_moves_each_step():
    engine = PongEngine()
    initial_x = engine.state.ball_x
    
    engine.step(PongInput(action="idle"))
    
    assert engine.state.ball_x != initial_x
```

Fast, no UI required, no network required.

---

## Summary

The Pong example shows the LEGO architecture at its most obvious:

1. **Contracts first** — define `PongInput` and `PongState` before writing any logic
2. **Pure engine** — game logic with zero external dependencies
3. **Adapters as plugs** — keyboard, neural net, API are all just adapters
4. **Same engine, different inputs** — the engine doesn't know or care who is driving it
5. **Easy to test** — pure logic means pure tests, no Flet or network needed

When you build your own services, follow the same pattern:
- Define contracts (what goes in, what comes out)
- Build pure logic (no UI, no DB imports)
- Write adapters (translate external input to contracts)
- Test the logic without the adapters
