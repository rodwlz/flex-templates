# FlexTemplates 2.0 — Dependency Injection Guide

## What Is Dependency Injection?

**Dependency Injection (DI)** is a pattern where you provide an object with what it needs from the outside, instead of the object creating those things itself.

**Bad (no DI):**
```python
class UserService:
    def __init__(self):
        self.db = Database()  # Service creates its own DB
        
service = UserService()
# Problem: UserService is tied to Database class forever
# Hard to test (can't use a fake DB)
# Hard to swap implementations
```

**Good (with DI):**
```python
class UserService:
    def __init__(self, db):  # DB is provided from outside
        self.db = db

# In production
db = Database()
service = UserService(db=db)

# In tests
fake_db = FakeDatabase()
service = UserService(db=fake_db)  # Same class, different DB!
```

The service doesn't care WHERE the db comes from. It just uses the `db` object given to it.

---

## The Problem DI Solves

Imagine you have this:

```python
# Old code (no DI)
class UserService:
    def create_user(self, username):
        db = Database()  # Creates its own connection
        repo = UserRepository(db)
        user = repo.create({"username": username})
        return user

class LoginView:
    def on_login_click(self):
        service = UserService()  # Creates a new service every time
        user = service.create_user("alice")
```

**Problems:**
1. `UserService` creates a new `Database` connection every call — wasteful
2. Each `LoginView` creates a new `UserService` — can't share one
3. Want to test with a fake DB? You'd have to modify `UserService` to accept one
4. Want to switch from PostgreSQL to MongoDB? Edit `UserService`? Broke LoginView too

**With DI:**

```python
# New code (with DI)
class UserService:
    def __init__(self, repo: UserRepository):  # Takes what it needs
        self.repo = repo
    
    def create_user(self, username):
        return self.repo.create({"username": username})

class LoginView:
    def __init__(self, service: UserService):  # Takes what it needs
        self.service = service
    
    def on_login_click(self):
        user = self.service.create_user("alice")

# In main.py — ONE place where everything is wired
db = Database()
repo = UserRepository(db=db)
service = UserService(repo=repo)
view = LoginView(service=service)

# In tests — swap out pieces
db_fake = FakeDatabase()
repo_fake = UserRepository(db=db_fake)
service_test = UserService(repo=repo_fake)
view_test = LoginView(service=service_test)  # Same view code, different innards
```

Now:
- `UserService` doesn't care if it's a real or fake repo
- `LoginView` doesn't care if it's a real or fake service
- One place (`main.py`) controls what gets wired together
- Tests can swap any piece

---

## The DI Container (dependency-injector library)

Writing `db = Database(); repo = ...; service = ...` in `main.py` gets tedious. The **DI container** automates it.

```python
from dependency_injector import containers, providers

# Define the container
class Container(containers.DeclarativeContainer):
    # Singleton: only one instance ever exists
    config = providers.Singleton(AppConfig)
    db = providers.Singleton(Database, config=config)
    
    # Factory: creates a new instance each time
    user_repo = providers.Factory(UserRepository, db=db)
    user_service = providers.Factory(UserService, repo=user_repo)

# Use it
container = Container()

# Get instances
service1 = container.user_service()
service2 = container.user_service()
# service1 and service2 are different instances (Factory)
# But they share the same db (Singleton)
```

### Provider Types

**Singleton** — one instance for the lifetime of the app:
```python
config = providers.Singleton(AppConfig)
db = providers.Singleton(Database, config=config)

db1 = container.db()
db2 = container.db()
assert db1 is db2  # Same object!
```

**Factory** — new instance each call:
```python
user_repo = providers.Factory(UserRepository, db=container.db())

repo1 = container.user_repo()
repo2 = container.user_repo()
assert repo1 is not repo2  # Different objects!
```

**Callable** — for functions:
```python
def get_current_user(token: str):
    return decode_jwt(token)

get_user = providers.Callable(get_current_user)
```

---

## FlexTemplates 2.0 Container

Here's what our container looks like:

```python
# flex_app/container.py

from dependency_injector import containers, providers
from flex_app.config.settings import AppConfig
from flex_app.config.vault import VaultManager
from flex_app.core.events import EventBus
from flex_app.database.session import SessionFactory
from flex_app.repositories.user_repository import UserRepository
from flex_app.services.user_service import UserService
from flex_app.services.navigation_service import NavigationService

class Container(containers.DeclarativeContainer):
    # ============ CONFIGURATION ============
    config = providers.Singleton(AppConfig)
    vault = providers.Singleton(VaultManager, key=config.provided.vault_key)
    
    # ============ CORE INFRASTRUCTURE ============
    event_bus = providers.Singleton(EventBus)
    
    # ============ DATABASE ============
    db_session_factory = providers.Singleton(
        SessionFactory,
        database_url=config.provided.database_url
    )
    
    # ============ REPOSITORIES ============
    user_repository = providers.Factory(
        UserRepository,
        session=db_session_factory.provided.session()
    )
    
    # ============ SERVICES ============
    navigation_service = providers.Singleton(
        NavigationService,
        event_bus=event_bus
    )
    
    user_service = providers.Factory(
        UserService,
        repository=user_repository,
        event_bus=event_bus
    )
    
    # ============ FLET UI (created only when app boots) ============
    nav_adapter = providers.Singleton(
        FletNavigationAdapter,
        navigation_service=navigation_service
    )
    
    flet_router = providers.Singleton(
        FletRouter,
        navigation_service=navigation_service
    )
```

**Reading this:**

- `config` is a Singleton — one AppConfig for the lifetime of the app
- `event_bus` is a Singleton — all services share the same event bus
- `user_repository` is a Factory — each call gets a fresh repo with its own session
- `user_service` is a Factory — each request gets a fresh service instance
- `navigation_service` is a Singleton — one shared history stack for the whole app

---

## Using the Container in Code

### In FastAPI (automatic via Depends)

```python
# api/routes/users.py

from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from flex_app.container import Container

router = APIRouter()

@router.post("/users")
@inject
async def create_user(
    username: str,
    service: UserService = Depends(Provide[Container.user_service])
):
    # FastAPI sees Depends(...) and calls container.user_service()
    # The same service instance is passed to this function
    result = service.execute(ActionRequest(action="create_user", data={"username": username}))
    return result.data
```

The `@inject` decorator and `Depends(Provide[...])` tell FastAPI:
- "This function needs a UserService"
- "Get it from the container"
- "It's a Factory, so give me a new one per request"

### In Flet Views (manual via props)

```python
# ui/router.py — FletRouter sets up views

def route_change(page):
    # When routing to /login, get the services and pass them as props
    props = {
        "user_service": container.user_service(),
        "navigation_service": container.navigation_service(),
    }
    
    # Import the view module and call view(page, props)
    from flex_app.views import login
    view_obj = login.view(page, props)
    page.views.append(view_obj)

# views/login.py

def view(page, props):
    # Services come in via props
    user_service = props["user_service"]
    nav_service = props["navigation_service"]
    
    # Use them
    def on_login(e):
        result = user_service.execute(ActionRequest(...))
        nav_service.execute(ActionRequest(action="visit", data={"url": "/home"}))
    
    return ft.Column([...])
```

### In Tests (no container, manual wiring)

```python
# tests/test_user_service.py

import pytest
from unittest.mock import Mock
from flex_app.services.user_service import UserService
from flex_app.core.events import EventBus

@pytest.fixture
def mock_repo():
    repo = Mock()
    repo.create.return_value = Mock(id=1, username="alice")
    return repo

@pytest.fixture
def service(mock_repo):
    bus = EventBus()
    return UserService(repository=mock_repo, event_bus=bus)

def test_create_user(service):
    result = service.execute(ActionRequest(action="create_user", data={"username": "alice"}))
    assert result.success == True
    assert result.data["id"] == 1
```

**Note:** In tests, you don't use the container. You manually wire up mocks and the real service. This keeps tests isolated and fast.

---

## Wiring the Container

At startup, the container needs to know about all the modules it will inject into. This is called "wiring":

```python
# flex_app/main.py

from flex_app.container import Container

def main():
    # Initialize the container
    container = Container()
    
    # Wire it to FastAPI routes + Flet views
    # This tells dependency-injector "look in these modules for @inject decorators"
    container.wire(
        modules=[
            "flex_app.api.routes.users",
            "flex_app.api.routes.products",
            "flex_app.views",  # All view modules
        ]
    )
    
    # Now FastAPI knows how to inject
    # Now Flet views can be loaded
```

---

## Common DI Patterns

### Pattern 1: Singleton for shared state (DB, config, event bus)

```python
db = providers.Singleton(Database, url=config.provided.database_url)

# Every service uses the same db connection
user_repo = providers.Factory(UserRepository, db=db)
product_repo = providers.Factory(ProductRepository, db=db)
# Both repos share the same DB connection
```

**When to use:** Databases, configs, loggers, caches, event buses.

### Pattern 2: Factory for stateless services

```python
user_service = providers.Factory(UserService, repository=user_repo)

# Each HTTP request gets a fresh service instance
# (but it shares the same repository/database)
```

**When to use:** Services, request handlers, anything that processes a single request.

### Pattern 3: Injecting into functions

```python
def get_current_user(token: str, service = Depends(Provide[Container.user_service])):
    # FastAPI injects the service
    return service.get_by_token(token)
```

### Pattern 4: Conditional wiring (different DB for tests)

```python
# In your test conftest.py
@pytest.fixture
def container():
    test_container = Container()
    # Override the database provider
    test_container.db_session_factory.override(
        providers.Singleton(InMemoryDatabase)
    )
    return test_container
```

---

## Real Example: Putting It All Together

### 1. Define contracts

```python
# contracts/user.py

class CreateUserRequest(BaseModel):
    username: str
    email: str

class UserOut(BaseModel):
    id: int
    username: str
```

### 2. Define repository (data access)

```python
# repositories/user_repository.py

from flex_app.models.user import User
from sqlalchemy.orm import Session

class UserRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, data: dict) -> User:
        user = User(username=data["username"], email=data["email"])
        self.session.add(user)
        self.session.commit()
        return user
```

### 3. Define service (business logic)

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
            try:
                user = self.repo.create(request.data)
                self.event_bus.publish(
                    Event(type="user.created", payload={"id": user.id})
                )
                return ActionResult(
                    success=True,
                    data={"id": user.id, "username": user.username}
                )
            except Exception as e:
                return ActionResult(success=False, error=str(e))
```

### 4. Wire in container

```python
# container.py

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(AppConfig)
    event_bus = providers.Singleton(EventBus)
    
    db_factory = providers.Singleton(
        SessionFactory,
        database_url=config.provided.database_url
    )
    
    user_repo = providers.Factory(
        UserRepository,
        session=db_factory.provided.session()
    )
    
    user_service = providers.Factory(
        UserService,
        repository=user_repo,
        event_bus=event_bus
    )
```

### 5. Use in API

```python
# api/routes/users.py

@router.post("/users")
@inject
async def create_user(
    username: str,
    email: str,
    service = Depends(Provide[Container.user_service])
):
    request = ActionRequest(action="create_user", data={"username": username, "email": email})
    result = service.execute(request)
    
    if not result.success:
        raise HTTPException(400, detail=result.error)
    
    return result.data
```

### 6. Test without the container

```python
# tests/test_user_service.py

def test_create_user():
    # Don't use container, wire manually
    mock_repo = Mock()
    mock_repo.create.return_value = Mock(id=1, username="alice")
    bus = EventBus()
    
    service = UserService(repository=mock_repo, event_bus=bus)
    
    result = service.execute(ActionRequest(action="create_user", data={"username": "alice", "email": "alice@example.com"}))
    
    assert result.success
    assert result.data["id"] == 1
```

---

## Rules of Thumb

1. **Containers define what gets wired, not how it's used.**
   - The container says "UserService needs a UserRepository"
   - The service doesn't care WHERE the repository comes from

2. **Pass dependencies, don't create them.**
   - Bad: `class Service: def __init__(self): self.repo = UserRepository()`
   - Good: `class Service: def __init__(self, repo): self.repo = repo`

3. **Singletons for shared resources (DB, config, cache). Factory for stateless services.**

4. **Tests don't use the container.**
   - Tests manually wire mocks and real objects
   - This keeps tests independent and fast

5. **One container per app.**
   - Define it once (container.py)
   - Wire it once (main.py)
   - Use it everywhere via `Depends(Provide[...])`

---

## Summary

**Dependency Injection = flexibility + testability**

- Instead of objects creating their own dependencies, they receive them
- The **container** manages creation and wiring
- Services receive interfaces, never concrete types
- Tests can swap in mocks without changing service code
- You can replace any layer (database, UI, API) without touching others

That's how FlexTemplates 2.0 achieves the LEGO philosophy — every piece can be swapped out because nothing is tightly coupled.
