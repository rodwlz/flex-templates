# FlexTemplates 2.0

A modern, LEGO-style framework combining **Flet** (UI), **FastAPI** (backend), **SQLAlchemy** (ORM), and **dependency injection** into a reusable, testable architecture for rapid application development.

**Goal:** Build desktop apps and REST APIs quickly, with clean separation of concerns and zero hardcoded imports.

---

## ⚡ Quick Start (5 minutes)

### 1. Install dependencies
```bash
pip install -e .
```

### 2. Run the app
```bash
python main.py
```

Opens a Flet desktop app + FastAPI backend on `localhost:8080`.

### 3. Run tests
```bash
pytest tests/ -v
```

All 142 tests pass, ~77% code coverage.

### 4. Check you're good to go
```bash
python -c "from lib.services.user_service import UserService; print('✓ Imports work')"
```

---

## 📁 What's in the Box

```
flex-templates-2/
│
├── README.md                          ← You are here
├── pyproject.toml                     ← Dependencies & entry points
├── main.py                            ← Boot sequence
│
├── lib/                               ← All business logic
│   ├── contracts/                     # Pydantic models (ActionRequest, ActionResult)
│   ├── core/                          # Interfaces (IService, IRepository)
│   ├── config/                        # Settings, vault, CLI
│   ├── database/                      # SQLAlchemy setup, ORM
│   ├── models/                        # User, Role ORM models
│   ├── repositories/                  # Data access (UserRepository, RoleRepository)
│   ├── services/                      # Business logic (UserService, RoleService)
│   ├── api/                           # FastAPI routes
│   ├── ui/                            # Flet components & routing
│   ├── views/                         # Flet pages (home, login, etc.)
│   └── container.py                   # DI container (wire everything here)
│
├── docs/                              ← Documentation
│   ├── QUICKSTART.md                  # 5-min cheat sheet
│   ├── API_ARCHITECTURE_SUMMARY.md    # How the API layer works
│   ├── API_PATTERN_TEMPLATE.md        # Step-by-step: add a new entity
│   ├── PONG_EXAMPLE.md                # Complete worked example
│   ├── api-docs/                      # Interactive HTML learning path
│   └── superpowers/                   # Implementation plans
│
└── tests/                             ← All tests
    ├── conftest.py                    # Test fixtures
    ├── test_services.py               # Service tests (no DB)
    ├── test_repositories.py           # Repository tests (in-memory SQLite)
    └── test_api.py                    # HTTP endpoint tests
```

---

## 🏗️ Architecture at a Glance

Every component communicates through **contracts** (Pydantic models), not direct function calls:

```
┌─────────────────────────────────────┐
│ Flet View or FastAPI Route          │
│ Sends: ActionRequest(action, data)  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Service (UserService, RoleService)  │
│ Returns: ActionResult(success, data)│
│ Uses: Repository.get(), .create()   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Repository (Data Access Layer)      │
│ Speaks: SQLAlchemy ORM, Sessions    │
└─────────────────────────────────────┘
```

**Rule:** Services receive `ActionRequest`, return `ActionResult`. Nothing crosses layers except these contracts.

---

## 🔑 Three Core Concepts

### 1. ActionRequest — "I want to do X"
```python
ActionRequest(action="create_user", data={"username": "alice", "email": "alice@example.com"})
```

### 2. ActionResult — "Here's what happened"
```python
ActionResult(success=True, data={"id": "123", "username": "alice"})
ActionResult(success=False, error="Username already taken")
```

### 3. Service Wrapper Methods — Convenience (no ActionRequest needed)
```python
# Old way (still works)
result = service.execute(ActionRequest(action="create_user", data={...}))

# New way (easier)
user = service.create_user(username="alice", email="alice@example.com")
roles = service.list_users()
success = service.delete_user(user_id)
```

---

## 🚀 Common Workflows

### I want to add a new REST endpoint

1. **Add a service method** (or use existing wrapper)
```python
# lib/services/my_service.py
def my_new_action(self, data: dict) -> dict:
    # business logic here
    return {"result": "..."}
```

2. **Wire it in the container**
```python
# lib/container.py
my_service = providers.Factory(MyService, ...)
```

3. **Add an API route**
```python
# lib/api/routes/my_route.py
@router.post("/my-endpoint")
@inject
async def my_endpoint(data: dict, service = Depends(Provide[Container.my_service])):
    try:
        result = service.my_new_action(data)
        return result
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
```

### I want to add a Flet view

1. **Create the view**
```python
# lib/views/my_view.py
def view(page, props):
    service = props["my_service"]
    
    def on_click(e):
        user = service.get_user(user_id="123")  # use wrapper method
        page.snack_bar = ft.SnackBar(ft.Text(f"Got {user['username']}"))
        page.snack_bar.open = True
        page.update()
    
    return ft.Column([ft.ElevatedButton("Click", on_click=on_click)])
```

2. **Router loads it automatically** — place it in `lib/views/my_view.py` and navigate to `/my_view`

### I want to add a database model

1. **Create the ORM model** (lib/models/my_model.py)
```python
from sqlalchemy import Column, String
from lib.database.base import Base

class MyModel(Base):
    __tablename__ = "my_models"
    name: Column[str] = Column(String(100))
```

2. **Create the repository** (lib/repositories/my_repository.py)
```python
from lib.repositories.base import AbstractRepository
from lib.models.my_model import MyModel

class MyRepository(AbstractRepository):
    model = MyModel
```

3. **Create the service** (lib/services/my_service.py)
```python
from lib.core.interfaces import SimpleService

class MyService(SimpleService):
    def __init__(self, factory):
        self._factory = factory
    
    def create(self, data: dict) -> dict:
        repo = MyRepository(self._factory)
        obj = repo.create(data)
        return {"id": str(obj.id)}
```

4. **Wire in container** (lib/container.py)
5. **Run migration**
```bash
alembic revision --autogenerate -m "add my_model table"
alembic upgrade head
```

---

## 🧪 Testing

### Test a service (no database)
```python
from unittest.mock import Mock
from lib.services.user_service import UserService
from lib.contracts.base import ActionRequest

def test_get_user():
    mock_repo = Mock()
    mock_repo.get.return_value = Mock(id="123", username="alice")
    
    service = UserService(factory=mock_repo)
    result = service.execute(ActionRequest(action="get", data={"id": "123"}))
    
    assert result.success == True
    assert result.data["username"] == "alice"
```

### Test a repository (in-memory SQLite)
```python
from lib.database.session import SessionFactory
from lib.repositories.user_repository import UserRepository

def test_create_user(db_factory):  # db_factory is in conftest.py
    repo = UserRepository(db_factory)
    user = repo.create({"username": "alice", "email": "alice@example.com"})
    
    assert user.id is not None
    assert user.username == "alice"
```

### Test an API endpoint
```python
from fastapi.testclient import TestClient
from lib.main import app

def test_api_create_user():
    client = TestClient(app)
    response = client.post("/users/create", json={
        "username": "alice",
        "email": "alice@example.com"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "alice"
```

**Run all tests:**
```bash
pytest tests/ -v --cov=lib --cov-report=term-missing
```

---

## 🎓 Learning Path

1. **[QUICKSTART.md](docs/QUICKSTART.md)** — 5-min cheat sheet (read this first!)
2. **[API_ARCHITECTURE_SUMMARY.md](docs/API_ARCHITECTURE_SUMMARY.md)** — How the API layer works
3. **[API_PATTERN_TEMPLATE.md](docs/API_PATTERN_TEMPLATE.md)** — Step-by-step: add a new entity from scratch
4. **[PONG_EXAMPLE.md](docs/PONG_EXAMPLE.md)** — Complete worked example (Pong game as API)
5. **[api-docs/](docs/api-docs/)** — Interactive HTML learning path (open in browser)

---

## 🔧 Key Files to Know

| File | Purpose |
|------|---------|
| `lib/container.py` | **ONLY place that names concrete classes.** Wire everything here. |
| `lib/contracts/base.py` | `ActionRequest`, `ActionResult`, `Event` — the LEGO plugs |
| `lib/core/interfaces.py` | `IService`, `IRepository` — abstract base classes |
| `lib/services/user_service.py` | Example service with immediate + staged operations |
| `lib/repositories/user_repository.py` | Example repository (CRUD + role operations) |
| `lib/api/routes/users.py` | Example API endpoints (immediate, staged, approval-required) |
| `tests/conftest.py` | Test fixtures (in-memory DB, services, repos) |

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'lib'"
```bash
# Make sure you're in the project root and installed in editable mode
pip install -e .
```

### "ImportError: cannot import name 'xyz' from 'lib.foo'"
```bash
# The import exists but not exported. Check:
# 1. Is the class defined in lib/foo/__init__.py?
# 2. Is there a circular import (A imports B, B imports A)?
# Use: grep -r "class xyz" lib/
```

### Tests fail with "database is locked"
```bash
# Concurrent test runs on SQLite. Use pytest-xdist with in-memory DB:
pytest tests/ -n auto  # Uses worker pool
# Or run serially:
pytest tests/ -v
```

### "Vault is locked" on startup
```bash
# The DI container tried to access vault before it was initialized
# Check main.py — vault.unlock() should come before service initialization
```

### Flet app doesn't connect to API
```bash
# Verify BackendServer is running:
# 1. Check main.py: server.start() called before ft.run()
# 2. Check FastAPI imports: @router.post, @router.get decorated
# 3. Check if port 8080 is available: netstat -an | grep 8080
```

---

## 📊 Project Stats

- **142 tests** — ~77% code coverage
- **6 service** operations (immediate + staged)
- **3 API endpoint types** (immediate, staged, approval-required)
- **2 ORM models** (User, Role) with many-to-many relationship
- **Zero hardcoded imports** — everything injected

---

## 🚧 What's Next?

- **Phase 2:** Add migrations (Alembic), Unit of Work pattern, more advanced services
- **Phase 3:** Event system for real-time updates
- **Phase 4:** Webhook support for external integrations
- **Phase 5:** GraphQL API option

See [docs/superpowers/](docs/superpowers/) for detailed implementation plans.

---

## 💡 Design Principles

1. **LEGO Architecture** — Every piece has clear inputs/outputs; swap parts without breaking others
2. **No Hardcoded Imports** — All wiring in one place (container.py)
3. **Contracts, Not Direct Calls** — Services speak ActionRequest/ActionResult
4. **Testability First** — Service = interface + impl; easy to mock the repo
5. **Convention Over Configuration** — Flet router auto-discovers views; API router auto-discovers routes
6. **Immutability Where It Matters** — Pydantic models are immutable; ORM objects are session-bound

---

## 📝 License

Part of FlexTemplates project.

---

## 🙋 Quick Questions?

**Q: Where do I add a new action to UserService?**
A: Add a method to `lib/services/user_service.py`, then wire it in `execute()`. Use wrapper methods for convenience.

**Q: How do I call a service from a view?**
A: Get it from props: `service = props["user_service"]`, then call wrapper method: `user = service.get_user(id)`.

**Q: How do I test a service without a database?**
A: Mock the repository: `repo = Mock()`, inject it, test the service logic in isolation.

**Q: Can I use the container in tests?**
A: No. Tests wire manually to avoid test interdependencies. The container is for production only.

**Q: What if I need to change a URL path?**
A: Edit the `@router.get()` or `@router.post()` decorator in `lib/api/routes/`, restart the server.

---

## 🔗 Navigation

- **Want to build fast?** → [QUICKSTART.md](docs/QUICKSTART.md)
- **Want to understand the API?** → [API_ARCHITECTURE_SUMMARY.md](docs/API_ARCHITECTURE_SUMMARY.md)
- **Want to add a new entity?** → [API_PATTERN_TEMPLATE.md](docs/API_PATTERN_TEMPLATE.md)
- **Want a complete example?** → [PONG_EXAMPLE.md](docs/PONG_EXAMPLE.md)
- **Want interactive docs?** → [docs/api-docs/](docs/api-docs/) (open index.html in browser)
