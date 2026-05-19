# FlexTemplates 2.0 — Contracts Guide

## What's a contract?

A **contract** is a fixed shape for data passing between layers. It defines what
goes in, what comes out, what fields are required, and what type each field is.

In FlexTemplates we use **Pydantic models** for contracts. Pydantic validates at
runtime — bad data is rejected at the boundary instead of crashing somewhere
deep in the stack.

A contract is to data what a function signature is to behaviour: a promise,
checkable, written once, read everywhere.

---

## Why contracts?

**Without contracts** every caller has to read the callee's source to know the
shape of the return value. When the callee changes, every caller breaks
silently.

**With contracts** the shape is the public surface. Callers depend on the
contract, not the implementation. The implementation can change freely as long
as the contract holds.

That's the property that makes the LEGO architecture work — every plug is a
contract, and you can swap any block as long as it produces the right shape.

---

## The three core contracts

Every layer-to-layer call uses one of these three. They live in
[lib/contracts/base.py](../lib/contracts/base.py):

```python
class Event(BaseModel):
    type: str                       # "user.created", "nav.route_changed"
    payload: dict[str, Any] = {}


class ActionRequest(BaseModel):
    action: str                     # "test", "visit", "set", "create"
    data: dict[str, Any] = {}       # Action-specific payload


class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    events: list[Event] = []
    error: str | None = None
```

That's the entire vocabulary the system uses to talk between layers. Every
service has the same `execute(request: ActionRequest) -> ActionResult`
signature, defined by `IService` in
[lib/core/interfaces.py](../lib/core/interfaces.py).

---

## A real walkthrough — testing a database connection

The admin databases view shows live status for every registered SQL connection.
Here's the full flow, top to bottom, using real code from the repo.

### 1. The view sends an `ActionRequest`

```python
# lib/views/admin/databases.py

def _probe(self, db_name: str) -> tuple[bool, float | None, str | None]:
    result = self.props["connection_tester"].execute(
        ActionRequest(action="test", data={"name": db_name})
    )
    d = result.data
    if d["alive"]:
        return True, d["latency_ms"], None
    return False, None, d["error"] or "connection failed"
```

The view doesn't know how the connection is tested. It builds a request, hands
it off, reads a result.

### 2. The service handles the action

```python
# lib/services/connection_tester.py

class ConnectionTester(SimpleService):
    """
    Actions: test
    test(data: {name}) -> {alive, latency_ms, error}
    """

    def test(self, data: dict) -> dict:
        try:
            factory = ConnectionRegistry.get(data["name"])
            start = time.time()
            with factory.session() as s:
                s.execute(text("SELECT 1"))
            return {
                "alive": True,
                "latency_ms": (time.time() - start) * 1000,
                "error": None,
            }
        except Exception as exc:
            return {"alive": False, "latency_ms": None, "error": str(exc)}
```

`ConnectionTester` extends `SimpleService` — a base class that routes
`request.action` to a same-named method automatically. So
`execute(ActionRequest(action="test", ...))` calls `self.test(...)`.

The method returns a plain dict. `SimpleService` wraps it as
`ActionResult(success=True, data=<dict>)`. Any exception that escapes becomes
`ActionResult(success=False, error=str(exc))`. The service never has to write
that boilerplate itself.

### 3. The registry is global lookup

```python
# lib/database/session.py

class ConnectionRegistry:
    _factories: dict[str, SessionFactory] = {}

    @classmethod
    def register(cls, url: str, name: str = "postgres", echo: bool = False):
        cls._factories[name] = SessionFactory(url, echo=echo)

    @classmethod
    def get(cls, name: str = "postgres") -> SessionFactory:
        ...
```

Registries are class-level singletons (no instances). Per
[CONVENTIONS.md §6](CONVENTIONS.md), they're exempt from the props-dict rule —
treat them as global lookup tables, not stateful services.

### 4. The wiring is in `main.py`

```python
# main.py

connection_tester = ConnectionTester()

router.set_props_factory(lambda: {
    "nav_service":       nav_service,
    "vault_service":     vault_service,
    "connection_tester": connection_tester,
    ...
})
```

One singleton instance, passed via the `props` dict the router gives every
view. The view never imports `ConnectionTester` — it only knows the contract.

---

## The HTTP angle — same service, different caller

Because the contract is the only public surface, an HTTP route can call the
same service the Flet view calls. Here's the cache-status endpoint
([lib/api/routes/caches.py](../lib/api/routes/caches.py)):

```python
from lib.contracts.base import ActionRequest
from lib.services.cache_registry import CacheRegistry
from lib.services.cache_tester import CacheTester

router = APIRouter(prefix="/caches", tags=["caches"])
_tester = CacheTester()


@router.get("/{name}")
def get_cache_status(name: str) -> dict:
    if name not in CacheRegistry.list():
        raise HTTPException(404, f"Cache adapter {name!r} not registered")
    result = _tester.execute(ActionRequest(action="test", data={"name": name}))
    return result.model_dump()
```

The HTTP route does the same thing the Flet view does: build an
`ActionRequest`, call `execute()`, return the result. The service has one
implementation, two consumers. That's the payoff for putting everything behind
a contract.

For the User resource, see [lib/api/routes/users.py](../lib/api/routes/users.py)
— uses `Depends(get_repo)` for per-request session scope, returns plain dicts
so the contract stays JSON-shaped.

---

## Pong — same engine, two drivers

Pong is the canonical proof. The engine ingests `PongInput` and produces
`PongState`. Two adapters produce `PongInput`: a keyboard reader and a fake
neural-net controller. Swapping one for the other is a one-line change.

### The contracts

```python
# games/contracts.py

class PongInput(BaseModel):
    left_up: bool = False
    left_down: bool = False
    right_up: bool = False
    right_down: bool = False


class PongState(BaseModel):
    ball_x: float = 400.0
    ball_y: float = 300.0
    ...
```

### The keyboard adapter

```python
# games/keyboard_adapter.py

class KeyboardAdapter:
    def __init__(self):
        self._keys: set[str] = set()

    def on_key(self, e) -> None:
        self._keys.add(e.key)

    def get_input(self, state: PongState | None = None) -> PongInput:
        return PongInput(
            left_up="W" in self._keys or "w" in self._keys,
            left_down="S" in self._keys or "s" in self._keys,
            right_up="Arrow Up" in self._keys,
            right_down="Arrow Down" in self._keys,
        )
```

### The mock neural adapter

```python
# games/mock_neural_adapter.py

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
```

Both adapters expose the exact same `get_input(state) -> PongInput`
signature. The view swaps them with a single line:

```python
adapter = KeyboardAdapter()         # human plays
# adapter = MockNeuralAdapter()     # AI plays — same engine, same view
```

The engine has zero imports from `lib`, zero awareness of who's driving,
zero awareness of who's rendering. The contracts are the only coupling.
That's the whole architectural pitch in 30 lines of code.

For the full walkthrough, see [docs/PONG_EXAMPLE.md](PONG_EXAMPLE.md).

---

## Building your own service

Most services should subclass `SimpleService` — one method per action, return
a dict, get free `ActionRequest` routing, free exception trapping, free
`ActionResult` wrapping.

```python
# Hypothetical OrderService — illustrating the pattern, not yet built

class OrderService(SimpleService):
    """
    Actions: create, cancel, get

    create(data: {customer_id, items}) -> {order_id, total}
    cancel(data: {order_id}) -> {cancelled: bool}
    get(data: {order_id}) -> {order_id, customer_id, items, total, status}
    """

    def __init__(self, repo: OrderRepository, event_bus: EventBus):
        self._repo = repo
        self._bus = event_bus

    def create(self, data: dict) -> dict:
        order = self._repo.create(data)
        self._bus.publish(Event(type="order.created", payload={"id": order.id}))
        return {"order_id": str(order.id), "total": order.total}

    def cancel(self, data: dict) -> dict:
        ok = self._repo.delete(data["order_id"])
        return {"cancelled": ok}

    def get(self, data: dict) -> dict:
        order = self._repo.get(data["order_id"])
        if order is None:
            raise RuntimeError(f"Order {data['order_id']!r} not found")
        return {"order_id": str(order.id), ...}
```

Three things to notice:

1. **No `execute` method** — `SimpleService` provides it, dispatches by name.
2. **Plain dicts, not `ActionResult`** — wrapping is automatic. Return an
   `ActionResult` directly if you need to populate `events` or pick a custom
   `success` value.
3. **Raise exceptions freely** — they become
   `ActionResult(success=False, error=str(exc))` so callers never see raw
   tracebacks. Domain errors should be raised, not branched into.

For services where the dispatcher would collide with an existing property
(like `NavigationService.current` which is both a property and an action), or
where every action needs custom `events` payloads, write a plain `IService`
with a `match request.action` block. See [CONVENTIONS.md §9](CONVENTIONS.md)
for the full guidance and `NavigationService` for the canonical example.

---

## Common mistakes

### Contracts importing implementation

```python
# WRONG — contracts must be pure data
from lib.repositories.user_repository import UserRepository

class UserOut(BaseModel):
    repo: UserRepository
```

`lib/contracts/` may only import `pydantic` and stdlib. If a contract reaches
into another layer, you've turned the contract into a wrapper for the thing
you're trying to abstract over.

### Services returning ORM objects

```python
# WRONG — leaks SQLAlchemy types into the consumer
def get_user(self, data: dict) -> User:
    return self.repo.get(data["id"])
```

Repositories return ORM objects. Services translate to plain data
(dicts or contract models) before returning.

### Contracts doing business validation

```python
# WRONG — Pydantic validators only check shape and type
class UserOut(BaseModel):
    username: str

    @field_validator("username")
    def must_exist_in_db(cls, v):  # business rule, not a contract concern
        ...
```

Pydantic checks "is this a string." The service checks "does this user exist."
Don't conflate the two.

### Reaching across the props dict

```python
# WRONG
nav = self.props["nav_service"]
nav._history.clear()  # poking private state of a service
```

If you need a behaviour, add an action to the service. Reaching into
private state means the contract is incomplete.

---

## Testing with contracts

Because every public surface is a contract, tests are explicit:

```python
# tests/test_connection_tester.py

def test_returns_alive_true_on_working_connection(working_db):
    result = ConnectionTester().execute(
        ActionRequest(action="test", data={"name": working_db})
    )
    assert result.success is True
    assert result.data["alive"] is True
    assert result.data["error"] is None
    assert result.data["latency_ms"] >= 0
```

No mocks of internal methods, no special fixtures, no patching. Build the
request, call `execute`, assert on the result fields. Because the contract is
the boundary, that's all there is to check.

For the full pattern with registry fixtures, see
[tests/test_connection_tester.py](../tests/test_connection_tester.py).

---

## Summary

- **Contracts are the only public surface.** Inside a layer, do whatever's
  cheapest — outside it, talk in `ActionRequest` / `ActionResult` / `Event`.
- **`SimpleService` is the default.** One method per action, plain-dict
  returns, free wrapping, free error trapping.
- **Registries are exempt from props.** They're class-level globals, treated
  more like config than like services. See
  [CONVENTIONS.md §6](CONVENTIONS.md).
- **Repositories don't know about contracts.** They return ORM objects.
  Services translate.
- **HTTP routes call services exactly like Flet views do** — build an
  `ActionRequest`, hand it off, return the result.
- **Test through the contract.** If your test mocks an internal method, the
  contract is leaking abstraction.

That's how the LEGO works. Every block has a contract on its plug; every
consumer programs to the plug. Swap any block, the rest of the system can't
tell.
