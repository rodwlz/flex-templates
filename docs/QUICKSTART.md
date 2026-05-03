# FlexTemplates 2.0 — Quick Start & Cheat Sheet

## The 5-Minute TL;DR

**FlexTemplates 2.0 has three layers that communicate via contracts:**

```
┌─────────────────────────────────────────┐
│ PRESENTATION (Views + API endpoints)    │
│ ↓ sends ActionRequest(action, data)     │
│ ↑ receives ActionResult(success, data)  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ BUSINESS LOGIC (Services)               │
│ ↓ uses Repositories to access data      │
│ ↑ returns ActionResult                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ DATA ACCESS (Repositories + ORM)        │
│ ↓ queries the database                  │
│ ↑ returns ORM objects                   │
└─────────────────────────────────────────┘
```

**Everything is injected via a DI container** — no hardcoded imports, no global singletons.

---

## The Three Contracts You Need to Know

### 1. ActionRequest — "I want to do X"

```python
from pydantic import BaseModel
from typing import Any

class ActionRequest(BaseModel):
    action: str                  # What to do
    data: dict[str, Any] = {}    # Parameters
```

**Example:**
```python
ActionRequest(action="create_user", data={"username": "alice", "email": "alice@example.com"})
ActionRequest(action="go_back")
ActionRequest(action="move_paddle", data={"direction": "up"})
```

### 2. ActionResult — "Here's what happened"

```python
class Event(BaseModel):
    type: str                           # What happened
    payload: dict[str, Any] = {}        # Details

class ActionResult(BaseModel):
    success: bool                       # Did it work?
    data: dict[str, Any] = {}           # Result (if success=True)
    events: list[Event] = []            # Notifications for listeners
    error: str | None = None            # Error (if success=False)
```

**Example:**
```python
# Success
ActionResult(
    success=True,
    data={"id": 42, "username": "alice"},
    events=[Event(type="user.created", payload={"id": 42})]
)

# Failure
ActionResult(success=False, error="Username already taken")
```

### 3. Event — "Something happened, here's the news"

```python
class Event(BaseModel):
    type: str                   # Event name
    payload: dict[str, Any] = {}  # Event data
```

Used by services to notify listeners (EventBus pattern).

---

## The Architecture in 5 Lines

```
View sends ActionRequest
  → Service.execute(request)
      → Repository does DB work
      → Service returns ActionResult with data + events
  → View gets ActionResult and updates UI
```

**That's it.** Everything else is plumbing to make this flow efficient, testable, and flexible.

---

## Common Tasks

### Add a new API endpoint

1. **Create a service method** (services/my_service.py)
   ```python
   def execute(self, request: ActionRequest) -> ActionResult:
       if request.action == "do_something":
           result = self.repo.do_something(request.data)
           return ActionResult(success=True, data=result)
   ```

2. **Add the FastAPI route** (api/routes/my_route.py)
   ```python
   @router.post("/my-endpoint")
   @inject
   async def my_endpoint(
       data: dict,
       service = Depends(Provide[Container.my_service])
   ):
       result = service.execute(ActionRequest(action="do_something", data=data))
       if not result.success:
           raise HTTPException(400, detail=result.error)
       return result.data
   ```

3. **Wire in the container** (container.py)
   ```python
   my_service = providers.Factory(MyService, repo=my_repo, event_bus=event_bus)
   ```

### Add a new Flet view

1. **Create the view** (views/my_view.py)
   ```python
   def view(page, props):
       service = props["my_service"]
       
       def on_click(e):
           result = service.execute(ActionRequest(action="...", data={...}))
           if result.success:
               # update UI
               pass
       
       return ft.Column([...])
   ```

2. **The router automatically loads it** (ui/router.py handles `/my_view` → views/my_view.py)

3. **Wire services to views** (ui/router.py)
   ```python
   props = {
       "my_service": container.my_service(),
       "other_service": container.other_service(),
   }
   ```

### Add a service

1. **Create the repository** (repositories/my_repository.py)
   ```python
   from flex_app.core.interfaces import IRepository
   
   class MyRepository(IRepository):
       def __init__(self, session):
           self.session = session
       
       def create(self, data: dict):
           # DB work
           obj = MyORM(...)
           self.session.add(obj)
           self.session.commit()
           return obj
   ```

2. **Create the service** (services/my_service.py)
   ```python
   from flex_app.core.interfaces import IService
   from flex_app.contracts.base import ActionRequest, ActionResult
   
   class MyService(IService):
       def __init__(self, repository, event_bus):
           self.repo = repository
           self.event_bus = event_bus
       
       def execute(self, request: ActionRequest) -> ActionResult:
           if request.action == "create":
               obj = self.repo.create(request.data)
               self.event_bus.publish(Event(type="my_obj.created", ...))
               return ActionResult(success=True, data={...})
   ```

3. **Wire it** (container.py)

   ```python
   my_repo = providers.Factory(MyRepository, session=db_session_factory.provided.session())
   my_service = providers.Factory(MyService, repository=my_repo, event_bus=event_bus)
   ```

### Test a service (no database needed)

```python
# tests/test_my_service.py

from unittest.mock import Mock
from flex_app.services.my_service import MyService
from flex_app.core.events import EventBus
from flex_app.contracts.base import ActionRequest

def test_create_my_obj():
    # Setup — manually wire with mocks
    mock_repo = Mock()
    mock_repo.create.return_value = Mock(id=1, name="test")
    event_bus = EventBus()
    
    service = MyService(repository=mock_repo, event_bus=event_bus)
    
    # Execute
    request = ActionRequest(action="create", data={"name": "test"})
    result = service.execute(request)
    
    # Assert
    assert result.success == True
    assert result.data["id"] == 1
```

---

## File Organization Cheat Sheet

```
flex_app/
├── contracts/              # Pydantic models — no imports except pydantic
│   ├── base.py            # ActionRequest, ActionResult, Event
│   ├── user.py            # UserIn, UserOut, UserCreate
│   └── ...
│
├── core/                  # Interfaces + infrastructure
│   ├── interfaces.py      # IService, IRepository, etc. (ABCs)
│   ├── events.py          # EventBus
│   └── patterns.py        # SingletonMeta, Registry
│
├── config/                # Configuration
│   ├── settings.py        # AppConfig (reads env + vault)
│   ├── vault.py           # VaultManager (encrypt/decrypt)
│   └── cli.py             # CLI commands (flex-encrypt, flex-decrypt)
│
├── database/              # ORM setup
│   ├── base.py            # SQLAlchemy Base
│   ├── session.py         # SessionFactory
│   └── migrations/        # Alembic versions
│
├── models/                # SQLAlchemy ORM tables
│   ├── user.py            # User ORM model
│   └── ...
│
├── repositories/          # Data access
│   ├── base.py            # AbstractRepository (generic ABC)
│   ├── user_repository.py # UserRepository
│   └── ...
│
├── services/              # Business logic
│   ├── user_service.py    # UserService
│   ├── navigation_service.py  # NavigationService
│   └── ...
│
├── api/                   # FastAPI layer
│   ├── server.py          # BackendServer (Uvicorn lifecycle)
│   ├── router_registry.py # Auto-discovers route modules
│   └── routes/
│       ├── users.py       # /users endpoints
│       └── ...
│
├── ui/                    # Flet layer
│   ├── adapter.py         # FletNavigationAdapter (binds page to service)
│   ├── error_handler.py   # FletErrorAdapter (shows errors)
│   ├── router.py          # FletRouter (URL → view lazy-import)
│   ├── components/        # LEGO pieces
│   │   ├── base.py        # FlexComponent ABC
│   │   ├── nav_bar.py     # NavBar
│   │   ├── side_bar.py    # SideBar
│   │   └── ...
│   └── layouts/
│       └── st_view.py     # StView (sidebar + navbar + content)
│
├── views/                 # Flet page modules
│   ├── home.py            # def view(page, props): ...
│   ├── login.py
│   └── ...
│
├── container.py           # DI container (only file naming concretes)
└── main.py                # Boot sequence
```

---

## DI Container Pattern

**Rule: container.py is the only file that says concrete class names.**

```python
# container.py — everything gets wired here

class Container(containers.DeclarativeContainer):
    # Singletons (one instance forever)
    config = providers.Singleton(AppConfig)
    event_bus = providers.Singleton(EventBus)
    
    # Factories (new instance per call)
    user_repo = providers.Factory(UserRepository, ...)
    user_service = providers.Factory(UserService, ...)
```

**Using it in FastAPI:**
```python
@inject
async def my_endpoint(service = Depends(Provide[Container.user_service])):
    # FastAPI calls container.user_service() and passes the result
```

**Using it in tests:**
```python
# Tests do NOT use the container
# Tests manually wire mocks
mock_repo = Mock()
service = UserService(repository=mock_repo, event_bus=EventBus())
```

---

## Pydantic Cheat Sheet

```python
from pydantic import BaseModel, Field
from typing import Any, Optional

# Basic model
class User(BaseModel):
    id: int
    username: str
    email: str

# Optional field
class UpdateUser(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None

# Default values
class Config(BaseModel):
    debug: bool = False
    port: int = 8080

# Any type (flexible)
class ActionRequest(BaseModel):
    action: str
    data: dict[str, Any] = {}

# Validation
user = User(id=1, username="alice", email="alice@example.com")  # works

try:
    bad_user = User(id="not a number", username="alice", email="alice@example.com")
except ValidationError:
    print("Invalid!")  # Pydantic caught the error

# Convert to dict
user_dict = user.model_dump()

# Parse from dict
user2 = User.model_validate({"id": 1, "username": "bob", "email": "bob@example.com"})
```

---

## Common Patterns

### Pattern 1: Service returns result or error

```python
def execute(self, request: ActionRequest) -> ActionResult:
    try:
        result = self.do_work(request.data)
        return ActionResult(success=True, data=result)
    except ValueError as e:
        return ActionResult(success=False, error=str(e))
```

### Pattern 2: Service publishes events for side effects

```python
def execute(self, request: ActionRequest) -> ActionResult:
    user = self.repo.create(request.data)
    self.event_bus.publish(Event(type="user.created", payload={"id": user.id}))
    return ActionResult(success=True, data={"id": user.id})
```

### Pattern 3: View handles service result

```python
def on_click(e):
    result = service.execute(request)
    if result.success:
        show_success(result.data)
    else:
        show_error(result.error)
```

### Pattern 4: API converts request/response

```python
@router.post("/users")
@inject
async def create_user(username: str, service = Depends(...)):
    # Convert HTTP input to contract
    request = ActionRequest(action="create_user", data={"username": username})
    
    # Call service
    result = service.execute(request)
    
    # Convert contract to HTTP output
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

---

## Key Rules

1. **Services receive ActionRequest, return ActionResult**
2. **Repositories don't know about contracts — they return ORM objects**
3. **Views don't import services directly — they receive via props**
4. **API endpoints don't know about ORM — they use service results**
5. **The container is the only place concrete types are named**
6. **Tests wire dependencies manually, never use the container**
7. **Contracts only import pydantic and stdlib — nothing else**
8. **EventBus is how services notify listeners without coupling**

---

## Debugging Checklist

**Service not getting called?**
- Is it wired in container.py?
- Is the action name matching? (case sensitive)

**Data shape wrong?**
- Check the contract definition (contracts/*.py)
- Use Pydantic validation: `Model.model_validate(data)` to catch errors early

**DI injection not working?**
- Is @inject decorator on the function?
- Is container.wire() called in main.py?
- Check the provider name in Depends(Provide[...])

**View not rendering?**
- Is the view function signature `def view(page, props):`?
- Is the view module in flex_app/views/?
- Does the filename match the URL? (/login → views/login.py)

**Test failing?**
- Don't use the container in tests — wire manually
- Use Mock() from unittest.mock for repositories
- Check ActionRequest.action name matches service logic

---

## Next Steps

1. **[Read ARCHITECTURE_AND_CONCEPTS.md](ARCHITECTURE_AND_CONCEPTS.md)** — Detailed explanation of EventBus, BaseView, FletRouter, async in Flet, and what's missing
2. **[Read ADDING_STUFF.md](ADDING_STUFF.md)** — Step-by-step recipes for common tasks
3. **[Read TESTING.md](TESTING.md)** — How to test, common failures, 5 quick fixes
4. **Review the plan** — C:\Users\rodwlz\.claude\plans\refactored-wibbling-forest.md
