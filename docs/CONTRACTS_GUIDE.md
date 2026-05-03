# FlexTemplates 2.0 — Contracts Guide

## What Are Contracts?

A **contract** is a promise about the shape of data. It defines:
- **What goes in** (inputs)
- **What comes out** (outputs)
- **What fields are required/optional**
- **What type each field is**

In FlexTemplates 2.0, we use **Pydantic models** for contracts. Pydantic is a Python library that validates data at runtime — it ensures that data matches the contract before your code even sees it.

Think of a contract like a function signature, but for data objects:

```python
# Traditional function signature (input/output types clear)
def add(a: int, b: int) -> int:
    return a + b

# Pydantic contract (data structure, input/output clear)
class AddRequest(BaseModel):
    a: int
    b: int

class AddResult(BaseModel):
    result: int
```

The function signature is a contract for function behavior. The Pydantic models are contracts for data shape.

---

## Why Contracts? The Problem They Solve

**Without contracts:**
```python
# View sends data to service
data = {"username": "alice", "age": 30}
result = user_service.create(data)

# What shape is result? Is it {"id": 42} or {"success": True, "id": 42, "errors": []}?
# You have to read the service code to know.
# If service changes, view breaks silently.
# Tests are hard because you don't know what to expect.
```

**With contracts:**
```python
# Define the contract first
class CreateUserRequest(BaseModel):
    username: str
    age: int

class CreateUserResult(BaseModel):
    id: int
    created_at: datetime

# View knows exactly what to send and what to expect
request = CreateUserRequest(username="alice", age=30)
result = user_service.create(request)

# Type hints + validation = confidence
# IDE autocomplete works
# Tests are explicit
```

---

## The Three Core Contracts in FlexTemplates 2.0

Every interaction between layers uses one of these three contracts:

### 1. ActionRequest — "I want to do something"

```python
from pydantic import BaseModel
from typing import Any

class ActionRequest(BaseModel):
    action: str                  # What operation: "create_user", "go_back", "move_paddle"
    data: dict[str, Any] = {}    # Payload (action-specific)

# Examples:
request1 = ActionRequest(action="create_user", data={"username": "alice", "age": 30})
request2 = ActionRequest(action="go_back")  # data defaults to {}
request3 = ActionRequest(action="move_paddle", data={"direction": "up"})
```

**Used by:** Views, API endpoints, game agents — anyone who wants to trigger an action.

---

### 2. ActionResult — "Here's what happened"

```python
class Event(BaseModel):
    type: str                           # "user.created", "nav.route_changed"
    payload: dict[str, Any] = {}        # Event data

class ActionResult(BaseModel):
    success: bool                       # Did it work?
    data: dict[str, Any] = {}           # The result (if success=True)
    events: list[Event] = []            # Side effects (for listeners to react to)
    error: str | None = None            # Error message (if success=False)

# Examples:
result1 = ActionResult(
    success=True,
    data={"id": 42, "username": "alice"},
    events=[Event(type="user.created", payload={"id": 42})]
)

result2 = ActionResult(
    success=False,
    error="Username already taken"
)
```

**Used by:** Services to return results from actions.

---

### 3. Event — "Something happened, listen up"

```python
class Event(BaseModel):
    type: str                   # e.g., "nav.route_changed", "game.score_updated"
    payload: dict[str, Any] = {}

# Example:
event = Event(
    type="nav.route_changed",
    payload={"url": "/login", "timestamp": 1234567890}
)
```

**Used by:** Services to notify listeners (NavigationService publishes, UI adapters subscribe).

---

## How Contracts Flow Through the System

### Example: Creating a User

#### 1. View (Flet UI) wants to create a user

```python
# views/login.py

from flex_app.contracts.base import ActionRequest

def view(page, props):
    user_service = props["user_service"]
    
    username_input = ft.TextField(label="Username")
    
    def on_signup(e):
        # Create a request contract
        request = ActionRequest(
            action="create_user",
            data={"username": username_input.value}
        )
        
        # Send it to the service (no direct DB calls!)
        result = user_service.execute(request)
        
        # Check the result
        if result.success:
            page.snack_bar.content.value = "User created!"
        else:
            page.snack_bar.content.value = f"Error: {result.error}"
        page.update()
    
    return ft.Column([
        username_input,
        ft.ElevatedButton("Sign Up", on_click=on_signup)
    ])
```

**Key point:** The view doesn't care HOW users are created. It just sends a request and expects a result.

---

#### 2. Service (business logic) processes the request

```python
# services/user_service.py

from flex_app.contracts.base import ActionRequest, ActionResult, Event
from flex_app.repositories.user_repository import UserRepository
from flex_app.core.events import EventBus

class UserService:
    def __init__(self, repository: UserRepository, event_bus: EventBus):
        self.repo = repository
        self.event_bus = event_bus
    
    def execute(self, request: ActionRequest) -> ActionResult:
        if request.action == "create_user":
            return self._create_user(request.data)
        return ActionResult(success=False, error="Unknown action")
    
    def _create_user(self, data: dict) -> ActionResult:
        try:
            # Call the repository
            user = self.repo.create(data)
            
            # Publish an event so listeners know
            self.event_bus.publish(
                Event(type="user.created", payload={"id": user.id})
            )
            
            # Return success with the user data
            return ActionResult(
                success=True,
                data={"id": user.id, "username": user.username},
                events=[Event(type="user.created", payload={"id": user.id})]
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))
```

**Key point:** The service receives a contract, does business logic, and returns a contract.

---

#### 3. Repository (data access) does the DB work

```python
# repositories/user_repository.py

from flex_app.core.interfaces import IRepository
from flex_app.models.user import User

class UserRepository(IRepository):
    def __init__(self, session):
        self.session = session
    
    def create(self, data: dict) -> User:
        # This is NOT a contract — it's internal
        # We talk to the DB and return a User ORM object
        user = User(username=data["username"])
        self.session.add(user)
        self.session.commit()
        return user
```

**Key point:** The repository doesn't know about contracts. It just works with ORM models. The service translates between contracts and ORM.

---

#### 4. API endpoint (HTTP layer) also uses contracts

```python
# api/routes/users.py

from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from flex_app.container import Container
from flex_app.contracts.base import ActionRequest

router = APIRouter(prefix="/users")

@router.post("/")
@inject
async def create_user(
    username: str,
    service = Depends(Provide[Container.user_service])
):
    # Convert HTTP request to contract
    request = ActionRequest(
        action="create_user",
        data={"username": username}
    )
    
    # Send to service
    result = service.execute(request)
    
    # Convert contract to HTTP response
    if not result.success:
        raise HTTPException(400, detail=result.error)
    
    return result.data  # {"id": 42, "username": "alice"}
```

**Key point:** HTTP request → contract → service → contract → HTTP response.

---

## The Data Path (Visual)

```
┌─────────────┐
│  Flet View  │
└──────┬──────┘
       │ sends ActionRequest(action="create_user", data={...})
       ▼
┌──────────────────┐
│  UserService     │
└──────┬───────────┘
       │ uses UserRepository
       ▼
┌──────────────────┐
│  UserRepository  │
└──────┬───────────┘
       │ returns User ORM object
       ▼
┌──────────────────┐
│  UserService     │
└──────┬───────────┘
       │ sends ActionResult(success=True, data={...}, events=[...])
       ▼
┌─────────────┐
│  Flet View  │
└──────┬──────┘
       │ shows snackbar
       ▼
    [User sees "User created!"]

ALSO (parallel):
┌──────────────────┐
│  EventBus        │  ← Service publishes Event(type="user.created")
└──────┬───────────┘
       │
       ▼
┌──────────────────────────┐
│  FletNavigationAdapter   │  ← Other listeners react to the event
└──────────────────────────┘
```

---

## The Pong Example (Contracts in Action)

Contracts really shine when the same logic drives different interfaces:

### Pong Contracts

```python
# games/contracts.py

class PongState(BaseModel):
    ball_x: float
    ball_y: float
    ball_vx: float
    ball_vy: float
    paddle_y: float
    score_left: int
    score_right: int

class PongInput(BaseModel):
    action: str  # "move_up", "move_down", "idle"
```

### Pong Engine (pure logic)

```python
# games/engine.py

class PongEngine:
    def __init__(self):
        self.state = PongState(
            ball_x=400, ball_y=300,
            ball_vx=5, ball_vy=5,
            paddle_y=275,
            score_left=0, score_right=0
        )
    
    def step(self, input: PongInput) -> PongState:
        # Update paddle
        if input.action == "move_up":
            self.state.paddle_y = max(0, self.state.paddle_y - 10)
        elif input.action == "move_down":
            self.state.paddle_y = min(580, self.state.paddle_y + 10)
        
        # Update ball physics
        self.state.ball_x += self.state.ball_vx
        self.state.ball_y += self.state.ball_vy
        
        # (collision detection here)
        
        return self.state
```

### Keyboard Driver (Flet)

```python
# games/keyboard_adapter.py

class KeyboardAdapter:
    def __init__(self, engine: PongEngine):
        self.engine = engine
    
    def on_key(self, e: ft.KeyboardEvent):
        # Translate Flet key event to contract
        action = "idle"
        if e.key == "ArrowUp":
            action = "move_up"
        elif e.key == "ArrowDown":
            action = "move_down"
        
        # Create contract
        input = PongInput(action=action)
        
        # Step engine (no Flet knowledge in engine!)
        state = self.engine.step(input)
        
        # Render state
        self.canvas.update(state)
```

### Neural Net Driver (RL agent)

```python
# games/neural_adapter.py

class NeuralAdapter:
    def __init__(self, engine: PongEngine, model):
        self.engine = engine
        self.model = model
    
    def step(self, observation):
        # Neural net predicts action
        raw_output = self.model(observation)  # [0.1, 0.8, 0.1]
        
        # Translate to contract
        actions = ["move_up", "move_down", "idle"]
        best_action = actions[raw_output.argmax()]
        input = PongInput(action=best_action)
        
        # Step engine (identical to keyboard driver!)
        state = self.engine.step(input)
        
        return state
```

**The magic:** The engine's `step()` method doesn't know if it's being driven by a keyboard or a neural net. Both send the same `PongInput` contract. The engine doesn't care about Flet or TensorFlow — it just returns `PongState`.

---

## How to Write Your Own Contracts

### 1. Identify the boundary

Ask: "What data flows between these two layers?"

```
View ← data → Service ← data → Repository
```

### 2. Write the contracts

```python
# contracts/user.py

from pydantic import BaseModel
from datetime import datetime

# Request: what the view sends to the service
class CreateUserRequest(BaseModel):
    username: str  # required
    email: str     # required
    age: int | None = None  # optional, defaults to None

# Response: what the service returns
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
```

### 3. Use them in services

```python
# services/user_service.py

def _create_user(self, data: dict) -> ActionResult:
    # Validate input using the contract
    request = CreateUserRequest(**data)  # Pydantic validates here
    
    # Do the work
    user = self.repo.create({
        "username": request.username,
        "email": request.email,
        "age": request.age
    })
    
    # Return with the response contract
    return ActionResult(
        success=True,
        data=UserOut.model_validate(user).model_dump()
    )
```

### 4. Type hints help

```python
# You get IDE autocomplete now
response: UserOut = UserOut(id=1, username="alice", email="alice@example.com", created_at=datetime.now())
print(response.username)  # IDE knows this exists, offers autocomplete
```

---

## Common Mistakes to Avoid

### Mistake 1: Mixing contracts with implementation details

```python
# BAD — contracts should not import business logic
from flex_app.repositories.user_repository import UserRepository

class UserOut(BaseModel):
    repo: UserRepository  # DON'T DO THIS
```

Contracts are pure data. They should only import:
- `pydantic` (BaseModel, Field, etc.)
- Python stdlib (datetime, etc.)
- Other contracts

### Mistake 2: Services returning ORM objects

```python
# BAD — views shouldn't know about ORM
from flex_app.models.user import User

def get_user() -> User:  # Returns ORM object
    return User(...)
```

**Good:**
```python
# GOOD — return via contract
def get_user(self, request: ActionRequest) -> ActionResult:
    user_orm = self.repo.get(...)
    return ActionResult(
        success=True,
        data={"id": user_orm.id, "username": user_orm.username}
    )
```

### Mistake 3: Contracts doing business validation

```python
# BAD — contracts shouldn't have business logic
class UserOut(BaseModel):
    username: str
    
    @field_validator("username")
    def username_must_exist_in_db(cls, v):  # DON'T DO THIS
        pass
```

**Good:**
```python
# Contracts only validate format/type
class UserOut(BaseModel):
    username: str  # Pydantic validates it's a string, that's enough

# Service validates business rules
def _create_user(self, data: dict) -> ActionResult:
    request = CreateUserRequest(**data)
    if self.repo.username_exists(request.username):  # service checks this
        return ActionResult(success=False, error="Username taken")
```

---

## Testing with Contracts

Contracts make testing way easier:

```python
# tests/test_user_service.py

from flex_app.contracts.base import ActionRequest, ActionResult
from flex_app.services.user_service import UserService
from unittest.mock import Mock

def test_create_user_success():
    # Setup
    mock_repo = Mock()
    mock_repo.create.return_value = Mock(id=1, username="alice")
    mock_bus = Mock()
    
    service = UserService(mock_repo, mock_bus)
    
    # Execute
    request = ActionRequest(
        action="create_user",
        data={"username": "alice"}
    )
    result = service.execute(request)
    
    # Assert — you KNOW what the result contract is
    assert result.success == True
    assert result.data["id"] == 1
    assert len(result.events) == 1
    assert result.events[0].type == "user.created"
```

Because everything is a contract, tests are explicit and easy to follow.

---

## Summary

**Contracts = data boundaries = clarity**

- Every layer communicates via Pydantic models
- No layer reaches across to another layer's internal types
- Services receive contracts, return contracts
- Repositories talk to DBs (no contracts), services translate
- Views talk to services via contracts
- APIs talk to services via contracts
- Tests are explicit about inputs/outputs

The benefit: **you can swap out any layer without changing others**. Replace Flet with a web UI? The services don't care — they return the same contracts. Replace SQLAlchemy with MongoDB? The services still return the same contracts.

That's the LEGO philosophy in action.
