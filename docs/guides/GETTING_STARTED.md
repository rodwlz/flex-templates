---
title: "Getting Started Guide"
category: guide
audience: [developer]
related:
  - ../core/ARCHITECTURE.md
  - QUICKSTART.md
agent_priority: low
---

# Getting Started with FlexTemplates 2.0

**Time: ~1 hour to go from zero to understanding**

This guide walks you through running the app, understanding the architecture, and making your first changes.

---

## Step 1: Setup (5 minutes)

### Clone & install
```bash
cd flex-templates
pip install -e .
```

### Verify the install
```bash
python -c "from lib.services.user_service import UserService; print('✓ Ready to go')"
```

---

## Step 2: Run the App (3 minutes)

### Start the app
```bash
python main.py
```

You'll see:
```
INFO: Uvicorn running on http://127.0.0.1:8080
INFO: Application startup complete
```

The Flet window opens + FastAPI backend is running.

### In the app:
1. Open the "Users" view
2. Click "Create User" button
3. See the form
4. Submit → Database saves the user
5. View refreshes to show the new user

**What just happened:** The UI called a service, which called a repository, which saved to the database. All through ActionRequest → ActionResult contracts.

---

## Step 3: Understand the Flow (10 minutes)

### Trace a button click

```
lib/views/users.py:
  on_click(e):
    # Step 1: Build the request
    request = ActionRequest(
        action="create_user",
        data={"username": "alice", "email": "alice@example.com"}
    )
    # Step 2: Call the service
    result = user_service.execute(request)
    # Step 3: Handle the result
    if result.success:
        page.update()  # refresh UI

lib/services/user_service.py:
  execute(request):  # receives ActionRequest
    if request.action == "create_user":
        # Step 4: Call repository
        repo = UserRepository(self._factory)
        user = repo.create(request.data)
        # Step 5: Return result
        return ActionResult(
            success=True,
            data={"id": user.id, "username": user.username}
        )

lib/repositories/user_repository.py:
  create(data):
    # Step 6: Database work
    user = User(username=data["username"], email=data["email"])
    self.session.add(user)
    self.session.commit()
    # Step 7: Return ORM object
    return user
```

**Key insight:** Each layer only talks to the next. Views don't import repositories. Services don't import ORM models directly (they get them from repos). Everything is injected.

---

## Step 4: Use the Wrapper Methods (5 minutes)

We just added convenience wrappers to make things easier. Compare:

### Old way (still works):
```python
result = user_service.execute(
    ActionRequest(action="get", data={"id": "123"})
)
user_id = result.data["id"]
```

### New way (easier):
```python
user = user_service.get_user("123")
user_id = user["id"]
```

### All wrapper methods:

**UserService:**
```python
user = user_service.get_user(user_id)
users = user_service.list_users()  # returns list of dicts
user = user_service.create_user(username, email)
success = user_service.delete_user(user_id)

# Staged (for complex operations)
preview = user_service.stage_user_with_roles(username, email, role_ids)
confirmed = user_service.confirm_staged()
cancelled = user_service.cancel_staged()
```

**RoleService:**
```python
role = role_service.get_role(role_id)
roles = role_service.list_roles()  # returns list of dicts
role = role_service.create_role(name, description)
success = role_service.delete_role(role_id)
```

---

## Step 5: Run the Tests (5 minutes)

### See what's tested
```bash
pytest tests/ -v --co
```

Shows all 142 tests.

### Run all tests
```bash
pytest tests/ -v
```

All pass. You'll see:
```
test_user_service.py::test_create_user PASSED
test_user_service.py::test_get_user PASSED
test_api.py::test_post_create_user PASSED
...
142 passed in 3.45s
```

### Run one test
```bash
pytest tests/test_services.py::TestUserService::test_create_user -v
```

### Run with coverage
```bash
pytest tests/ --cov=lib --cov-report=term-missing
```

Shows ~77% coverage. Good sign — not testing infrastructure, only logic.

---

## Step 6: Make Your First Change (15 minutes)

### Scenario: Add a "get_user_by_email" wrapper

1. **Open the UserService**
```bash
# lib/services/user_service.py
```

2. **Add the wrapper method** (before the closing `class` bracket)
```python
def get_user_by_email(self, email: str) -> dict | None:
    """Convenience method to find a user by email."""
    users = self.list_users()
    for user in users:
        if user["email"] == email:
            return user
    return None
```

3. **Test it** (in Python REPL or a test file)
```python
from lib.database.session import SessionFactory
from lib.services.user_service import UserService

factory = SessionFactory("sqlite:///dev.db")
service = UserService(factory)

user = service.get_user_by_email("alice@example.com")
print(user)  # {"id": "...", "username": "...", "email": "alice@example.com"}
```

4. **Use it in a view**
```python
# lib/views/users.py (find where you check email)
user = user_service.get_user_by_email(email_input.value)
if user:
    show_snackbar(f"Found {user['username']}")
else:
    show_snackbar("User not found")
```

---

## Step 7: Understand the Key Files (10 minutes)

### 1. Contracts (lib/contracts/base.py)
```python
# This is how everything talks
class ActionRequest(BaseModel):
    action: str
    data: dict[str, Any] = {}

class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    error: str | None = None
```

**Why:** Both Flet and FastAPI use the same contracts. Same business logic, different UI.

### 2. Container (lib/container.py)
```python
# This is where EVERYTHING gets wired
class Container(containers.DeclarativeContainer):
    config = providers.Singleton(AppConfig)
    user_repo = providers.Factory(UserRepository, ...)
    user_service = providers.Factory(UserService, user_repo=user_repo, ...)
```

**Why:** Only one place to change. Want to swap UserRepository for a different one? Change one line here.

### 3. Services (lib/services/)
```python
# Business logic lives here
class UserService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory
    
    def create(self, data: dict) -> dict:
        # Your business logic
        repo = UserRepository(self._factory)
        user = repo.create(data)
        return {"id": str(user.id)}
```

**Why:** Easy to test — just mock the factory, call the service.

### 4. Repositories (lib/repositories/)
```python
# Data access lives here
class UserRepository(AbstractRepository):
    model = User
    
    def create(self, data: dict) -> User:
        # Your ORM logic
        user = User(**data)
        self.session.add(user)
        self.session.commit()
        return user
```

**Why:** If you want to change databases, you only change the repositories.

---

## Step 8: Debug Your First Problem (10 minutes)

### Scenario: Your new wrapper method crashes

```python
user = user_service.get_user_by_email("alice@example.com")
# AttributeError: 'NoneType' object has no attribute '__getitem__'
```

**Debug checklist:**

1. **Does the method exist?**
```bash
grep -n "def get_user_by_email" lib/services/user_service.py
```

2. **Is it wired in the container?**
```bash
grep -n "user_service" lib/container.py
```

3. **What's actually being called?**
```python
# Add a print statement
def get_user_by_email(self, email: str):
    users = self.list_users()
    print(f"DEBUG: users = {users}")  # See what we got
    for user in users:
        print(f"DEBUG: checking {user['email']} == {email}")
        if user["email"] == email:
            return user
    return None
```

4. **Run the test again**
```bash
# Look at the debug output
# If users is empty → database has no users
# If None is returned → no email match (typo in email?)
```

5. **Check the repository**
```bash
# Did list() actually return users?
from lib.repositories.user_repository import UserRepository
from lib.database.session import SessionFactory

factory = SessionFactory("sqlite:///dev.db")
repo = UserRepository(factory)
all_users = repo.list()
print(f"DB has {len(all_users)} users")
for u in all_users:
    print(f"  {u.username}: {u.email}")
```

---

## Step 9: Read the Code (15 minutes)

In this order:

1. **[lib/contracts/base.py](../lib/contracts/base.py)** — The contracts (ActionRequest, ActionResult)
2. **[lib/services/user_service.py](../lib/services/user_service.py)** — A complete service example
3. **[lib/repositories/user_repository.py](../lib/repositories/user_repository.py)** — A repository example
4. **[lib/api/routes/users.py](../lib/api/routes/users.py)** — API endpoints using the service
5. **[lib/views/home.py](../lib/views/home.py)** — A Flet view using the service

Each is ~100 lines. See how they talk to each other.

---

## Step 10: Do the Exercises (remaining time)

### Exercise 1: Add a wrapper method (5 min)
Add `get_role_by_name(name)` to RoleService. Test it.

### Exercise 2: Use it in the UI (10 min)
Add a Flet control that searches for a role by name. Wire it up.

### Exercise 3: Add an API endpoint (15 min)
Add a `GET /roles/by-name/{name}` endpoint that uses the role service.

### Exercise 4: Write a test (10 min)
Test the new endpoint with httpx.AsyncClient.

---

## Common Questions at This Point

**Q: Where does `user_service` come from in the view?**
A: It's in `props`. The router injects it. See [lib/ui/router.py](../lib/ui/router.py).

**Q: What if I want to add a field to User?**
A: 1) Edit `lib/models/user.py` 2) Run `alembic revision --autogenerate -m "add field"` 3) Run `alembic upgrade head`

**Q: Can I use this for web apps (Flask, Django)?**
A: Yes! The services and repositories work anywhere. The contracts are framework-agnostic.

**Q: Is the database production-ready?**
A: For dev: yes (SQLite). For prod: switch to PostgreSQL (change one connection string).

**Q: How do I deploy this?**
A: Flet: package with `flet build` → exe/dmg. FastAPI: docker + gunicorn. See [docs/DEPLOYMENT.md](ONBOARDING_DEPLOYMENT.md).

---

## You're Done! 🎉

You now understand:

- ✅ How the architecture works (contracts, services, repos)
- ✅ How to run the app and tests
- ✅ How to use wrapper methods for convenience
- ✅ How to make a change (add a method, test it)
- ✅ How to debug (traces, print statements, repo checks)
- ✅ Where to find examples (the code itself)

**Next:** Read [docs/API_PATTERN_TEMPLATE.md](../examples/API_PATTERN_TEMPLATE.md) to learn how to add a whole new entity from scratch.

**Questions?** Check [docs/QUICKSTART.md](QUICKSTART.md) — it's a cheat sheet.
