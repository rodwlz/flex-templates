# FlexTemplates Anti-Patterns Guide

A guide to common mistakes in FlexTemplates and how to fix them. Read this to learn what *not* to do and why the patterns in [CONVENTIONS.md](CONVENTIONS.md) matter.

---

## Overview

FlexTemplates developers make predictable mistakes:
- **Services**: Hardcoded imports, service-calling-service, skipping repositories
- **Repositories**: Returning raw ORM objects, session leaks, no abstraction
- **Views**: Importing services directly, making HTTP calls inside handlers, missing error handling
- **Container/Wiring**: Multiple containers, service imports service, mixing test mocks in production

This guide shows the problem, why it breaks, the correct way, and the benefits. Every anti-pattern has before/after code.

---

## Service Anti-Patterns

### Anti-Pattern 1: Hardcoded Imports in Services

**The Problem**

Importing a service class directly inside another service, burning the dependency into the class definition:

```python
# WRONG — hardcoded import
from lib.services.user_service import UserService

class RoleService(SimpleService):
    def assign_role_to_user(self, data: dict) -> dict:
        user_service = UserService()  # Creates without injecting factory
        result = user_service.execute(ActionRequest(action="get", data={"id": data["user_id"]}))
        if not result.success:
            raise ValueError(result.error)
        # ... rest of logic
```

**Why It Breaks**

1. **No dependency injection**: `UserService()` has no factory, so it fails at runtime
2. **Testing becomes impossible**: You can't inject a mock `UserService` into `RoleService` for unit tests
3. **Circular imports**: If `UserService` imports `RoleService`, you get a circular dependency
4. **Tight coupling**: Code breaks if `UserService.__init__` changes its signature
5. **Duplication**: Each service that needs `UserService` hardcodes the import

**The Correct Way**

Pass services through the constructor (dependency injection):

```python
# CORRECT — injected dependency
class RoleService(SimpleService):
    def __init__(self, factory: SessionFactory, user_service: UserService):
        self._factory = factory
        self._user_service = user_service

    def assign_role_to_user(self, data: dict) -> dict:
        result = self._user_service.execute(ActionRequest(action="get", data={"id": data["user_id"]}))
        if not result.success:
            raise ValueError(result.error)
        # ... rest of logic
```

Then wire it in `main.py`:

```python
def main():
    factory = ConnectionRegistry.get()
    user_service = UserService(factory)
    role_service = RoleService(factory, user_service)
    # Now role_service.user_service is the injected instance
```

For stateless singletons (like `ConnectionTester`, `CacheTester`), class-level singletons are OK:

```python
# OK — stateless probes with no state
class ConnectionTester(SimpleService):
    def test(self, data: dict) -> dict:
        name = data["name"]
        factory = ConnectionRegistry.get(name)  # Registry is a class-level singleton
        return {"alive": test_connection(factory)}
```

**Benefits**

- ✅ Easy to test: inject mock services in tests
- ✅ No circular imports: services depend only on contracts and interfaces
- ✅ Flexible: swap implementations without changing code
- ✅ Explicit: dependencies are clear in `__init__`

---

### Anti-Pattern 2: Service Calling Service (Without DI)

**The Problem**

A service creates or imports another service directly, instead of using the injected instance:

```python
# WRONG — service creates another service internally
from lib.services.role_service import RoleService

class UserService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory
        self._role_service = RoleService(factory)  # Created here, not injected

    def create_with_roles(self, data: dict) -> dict:
        # Create user
        repo = UserRepository(self._factory)
        user = repo.create(data)
        # Assign default roles
        self._role_service.execute(ActionRequest(action="assign", data={"user_id": user.id}))
        return {"user_id": user.id}
```

**Why It Breaks**

1. **Hidden dependencies**: Callers don't know `UserService` needs `RoleService`
2. **State sharing**: If `RoleService` has state, both services share the same instance (subtle bugs)
3. **Testing fails**: Can't inject a test mock of `RoleService` into `UserService`
4. **Scaling**: Adding a third service that depends on `UserService` creates a nested dependency nightmare

**The Correct Way**

Inject the dependency explicitly:

```python
# CORRECT — RoleService is injected
class UserService(SimpleService):
    def __init__(self, factory: SessionFactory, role_service: RoleService):
        self._factory = factory
        self._role_service = role_service

    def create_with_roles(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.create(data)
        # Use the injected role_service
        self._role_service.execute(ActionRequest(action="assign", data={"user_id": user.id}))
        return {"user_id": user.id}
```

Wire in `main.py`:

```python
def main():
    factory = ConnectionRegistry.get()
    role_service = RoleService(factory)
    user_service = UserService(factory, role_service)
```

Or use a `StagingService` to handle multi-step logic:

```python
# BETTER — if the flow is complex, use StagingService to orchestrate
class UserService(StagingService):
    def __init__(self, factory: SessionFactory):
        # StagingService only takes factory, not email_service
        super().__init__(factory)
    
    def _stage_impl(self, uow, data: dict) -> dict:
        repo = uow.repo(UserRepository)
        role_repo = uow.repo(RoleRepository)
        
        user = repo.create(data)
        if role_ids := data.get("role_ids"):
            for role_id in role_ids:
                role = role_repo.get(role_id)
                if role:
                    user.roles.append(role)
        
        return {"user_id": user.id, "role_count": len(user.roles)}
```

If you need to inject `email_service`, do it at the container level in `main.py`, not in the service constructor.

**Benefits**

- ✅ Dependencies are explicit: callers see what's needed
- ✅ Testable: inject mocks of `RoleService`
- ✅ Maintainable: adding a third dependency doesn't create a chain
- ✅ Clear flow: `main.py` shows the complete wiring

---

### Anti-Pattern 3: Service with No Repository (Direct ORM Access)

**The Problem**

A service talks directly to the ORM, skipping the repository layer:

```python
# WRONG — service touches ORM directly
from sqlalchemy import select
from lib.database.session import SessionFactory
from lib.models.user import User

class UserService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def get_user(self, data: dict) -> dict:
        with self._factory.session() as s:
            # Direct ORM query instead of repository
            stmt = select(User).where(User.id == data["id"])
            user = s.execute(stmt).scalar_one_or_none()
            if not user:
                raise ValueError("User not found")
            return {"id": user.id, "name": user.name}

    def list_users(self, data: dict) -> dict:
        with self._factory.session() as s:
            # Another direct query
            users = s.query(User).all()
            return {"users": [{"id": u.id, "name": u.name} for u in users]}
```

**Why It Breaks**

1. **No abstraction**: Query logic is scattered; changes to `User` model break multiple services
2. **Not testable**: Can't mock the database layer — you must set up real ORM
3. **Duplication**: Every service that touches `User` repeats the same query patterns
4. **No caching layer**: Can't add a repository-level cache without rewriting all services
5. **Leaky abstraction**: Service knows about ORM details (sqlalchemy syntax, session management)

**The Correct Way**

Always use a repository:

```python
# CORRECT — service uses repository
class UserService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def get(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.get(uuid.UUID(data["id"]))
        if not user:
            raise ValueError(f"User {data['id']} not found")
        return {"id": str(user.id), "username": user.username, "email": user.email}

    def list(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        users = repo.list()
        return {"users": [{"id": str(u.id), "username": u.username} for u in users]}
```

Repository handles all ORM details:

```python
# Repository layer — all ORM logic lives here
class UserRepository(AbstractRepository[User]):
    model = User

    def get(self, id) -> User | None:
        with self._factory.session() as s:
            return s.get(self.model, id)

    def list(self, **filters) -> list[User]:
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)
            return q.all()
```

For complex queries, add repository methods:

```python
class UserRepository(AbstractRepository[User]):
    model = User

    def list_by_role(self, role_name: str) -> list[User]:
        """All users with a specific role."""
        with self._factory.session() as s:
            return s.query(self.model).join(Role, self.model.roles)\
                .filter(Role.name == role_name).all()

    def search_by_username(self, pattern: str) -> list[User]:
        """Users matching a username pattern."""
        with self._factory.session() as s:
            return s.query(self.model)\
                .filter(self.model.username.ilike(f"%{pattern}%")).all()
```

Services call repository methods, not ORM:

```python
class UserService(SimpleService):
    def search(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        users = repo.search_by_username(data["pattern"])
        return {"users": [{"id": str(u.id), "username": u.username} for u in users]}
```

**Benefits**

- ✅ Single source of truth: all `User` queries in one file
- ✅ Easy to test: mock `UserRepository` without touching the ORM
- ✅ Maintainable: change the ORM query once, all services benefit
- ✅ Composable: repositories can be chained, cached, or wrapped
- ✅ Swappable: can replace with a different data source (REST API, file store) without touching services

---

### Anti-Pattern 4: ActionRequest Chains Inside Methods

**The Problem**

A service method calls `execute()` with another `ActionRequest`, instead of calling the underlying method directly:

```python
# WRONG — chaining ActionRequests inside a method
class UserService(SimpleService):
    def create_and_welcome(self, data: dict) -> dict:
        # Create user via execute
        create_result = self.execute(ActionRequest(action="create", data=data))
        if not create_result.success:
            raise ValueError(create_result.error)
        
        # Send welcome email via execute (within the same service!)
        email_result = self.execute(ActionRequest(action="send_welcome_email", data={
            "user_id": create_result.data["id"],
            "email": data["email"],
        }))
        if not email_result.success:
            raise ValueError(email_result.error)
        
        return {"user_id": create_result.data["id"], "welcome_sent": True}

    def create(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.create(data)
        return {"id": str(user.id)}

    def send_welcome_email(self, data: dict) -> dict:
        # Actually send email
        send_email(data["email"], "Welcome!")
        return {"sent": True}
```

**Why It Breaks**

1. **Double wrapping**: `execute()` calls already wrap exceptions — chaining adds noise
2. **Serialization overhead**: `ActionRequest` is meant for API boundaries, not internal calls
3. **Testing complexity**: Mocking `execute()` is harder than mocking the underlying method
4. **Obfuscation**: The real call flow is hidden inside the framework plumbing
5. **Error handling**: Errors get wrapped twice, making debugging harder

**The Correct Way**

Call methods directly if they're in the same service:

```python
# CORRECT — call the method directly
class UserService(SimpleService):
    def create_and_welcome(self, data: dict) -> dict:
        user_data = self.create(data)  # Direct call
        self.send_welcome_email({
            "user_id": user_data["id"],
            "email": data["email"],
        })  # Direct call
        return {"user_id": user_data["id"], "welcome_sent": True}

    def create(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.create(data)
        return {"id": str(user.id)}

    def send_welcome_email(self, data: dict) -> dict:
        send_email(data["email"], "Welcome!")
        return {"sent": True}
```

If methods are in *different* services, use dependency injection:

```python
# Multiple services need coordination — inject the email service
class EmailService(SimpleService):
    def send(self, data: dict) -> dict:
        send_email(data["email"], data["subject"])
        return {"sent": True}

class UserService(SimpleService):
    def __init__(self, factory: SessionFactory, email_service: EmailService):
        self._factory = factory
        self._email_service = email_service

    def create_and_welcome(self, data: dict) -> dict:
        user_data = self.create(data)
        # Call email service directly
        result = self._email_service.execute(ActionRequest(
            action="send",
            data={"email": data["email"], "subject": "Welcome!"}
        ))
        if not result.success:
            raise ValueError(result.error)
        return {"user_id": user_data["id"], "welcome_sent": result.data["sent"]}
```

Or use a `StagingService` to orchestrate complex flows:

```python
# For complex multi-step flows, use StagingService
class UserService(StagingService):
    def __init__(self, factory: SessionFactory, email_service: EmailService):
        super().__init__(factory)
        self._email_service = email_service

    def _stage_impl(self, uow, data: dict) -> dict:
        repo = uow.repo(UserRepository)
        user = repo.create(data)
        # Stage email send
        email_result = self._email_service.execute(ActionRequest(
            action="send",
            data={"email": data["email"], "subject": "Welcome!"}
        ))
        return {"user_id": str(user.id), "email_sent": email_result.success}
```

**Benefits**

- ✅ Clear call flow: no hidden framework overhead
- ✅ Easier to test: mock the method directly
- ✅ Better error messages: exceptions aren't double-wrapped
- ✅ More composable: natural method chaining, no request serialization
- ✅ Explicit dependencies: inject services that are actually needed

---

### Anti-Pattern 5: Complex Query Logic in Service Methods

**The Problem**

A service method contains SQL-like logic instead of delegating to the repository:

```python
# WRONG — service has ORM logic
class UserService(SimpleService):
    def find_inactive_admins(self, data: dict) -> dict:
        """Find admins who haven't logged in for 30 days."""
        with self._factory.session() as s:
            from datetime import datetime, timedelta
            from lib.models.user import User
            from lib.models.role import Role
            
            threshold = datetime.utcnow() - timedelta(days=30)
            users = s.query(User)\
                .join(Role, User.roles)\
                .filter(Role.name == "admin")\
                .filter(User.last_login < threshold)\
                .all()
            
            return {
                "users": [{"id": str(u.id), "name": u.username} for u in users]
            }

    def get_user_summary(self, data: dict) -> dict:
        """Get user and role count."""
        with self._factory.session() as s:
            from lib.models.user import User
            
            user = s.get(User, data["id"])
            if not user:
                raise ValueError("User not found")
            
            return {
                "id": str(user.id),
                "name": user.username,
                "role_count": len(user.roles),
                "admin": "admin" in [r.name for r in user.roles],
            }
```

**Why It Breaks**

1. **Duplication**: The same query appears in multiple services
2. **Maintenance nightmare**: Change the `User` schema, fix the query in 10 places
3. **Testing**: Can't test query logic without a real database
4. **Performance**: No way to optimize queries globally (missing indexes, N+1 queries)
5. **Mixing concerns**: Service should orchestrate, not query

**The Correct Way**

Move all query logic to the repository:

```python
# Repository — all query logic lives here
class UserRepository(AbstractRepository[User]):
    model = User

    def find_inactive_admins(self, days: int = 30) -> list[User]:
        """Find admins who haven't logged in for N days."""
        from datetime import datetime, timedelta
        
        threshold = datetime.utcnow() - timedelta(days=days)
        with self._factory.session() as s:
            return s.query(self.model)\
                .join(Role, self.model.roles)\
                .filter(Role.name == "admin")\
                .filter(self.model.last_login < threshold)\
                .all()

    def get_with_summary(self, id) -> User | None:
        """Get user with eager-loaded roles."""
        with self._factory.session() as s:
            return s.get(self.model, id)  # Assumes roles are already loaded (lazy or joined)

    def is_admin(self, id) -> bool:
        """Check if user has admin role."""
        with self._factory.session() as s:
            user = s.get(self.model, id)
            if not user:
                return False
            return any(r.name == "admin" for r in user.roles)
```

Service calls repository methods:

```python
class UserService(SimpleService):
    def find_inactive_admins(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        users = repo.find_inactive_admins(days=data.get("days", 30))
        return {
            "users": [{"id": str(u.id), "name": u.username} for u in users]
        }

    def get_user_summary(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.get_with_summary(uuid.UUID(data["id"]))
        if not user:
            raise ValueError("User not found")
        
        return {
            "id": str(user.id),
            "name": user.username,
            "role_count": len(user.roles),
            "admin": repo.is_admin(user.id),
        }
```

**Benefits**

- ✅ Single source of truth: each query written once
- ✅ Easier to optimize: change one query, all services benefit
- ✅ Testable: can mock repository methods
- ✅ Reusable: multiple services can call the same query
- ✅ Maintainable: schema changes affect only repository, not services

---

## Repository Anti-Patterns

### Anti-Pattern 6: Repository Returning Raw ORM Objects

**The Problem**

A repository returns ORM model instances directly, leaking database concerns into the caller:

```python
# WRONG — repository returns ORM instances
class UserRepository(AbstractRepository[User]):
    model = User

    def get_with_roles(self, id) -> User:
        """Returns the ORM User object directly."""
        with self._factory.session() as s:
            user = s.get(self.model, id)
            return user  # Returns ORM instance; caller sees internal __dict__
```

Service receives the ORM object:

```python
class UserService(SimpleService):
    def get_user(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.get_with_roles(data["id"])
        
        # Problem: After the session closes, accessing user.roles triggers a lazy-load error
        return {
            "id": user.id,
            "roles": [r.name for r in user.roles],  # LAZY LOAD OUTSIDE SESSION — ERROR
        }
```

**Why It Breaks**

1. **Lazy loading errors**: Accessing relationships outside the session context fails
2. **Session leaks**: The ORM session is open longer than it should be
3. **Exposing internals**: Callers shouldn't know about ORM; they only need dicts
4. **Accidental mutations**: Caller modifies `user.name`, changes the database
5. **Serialization issues**: Can't JSON serialize the ORM object directly

**The Correct Way**

Repository returns dicts, not ORM objects:

```python
# CORRECT — repository returns dicts
class UserRepository(AbstractRepository[User]):
    model = User

    def get_with_roles(self, id) -> dict | None:
        """Returns a plain dict; all ORM access is in this method."""
        with self._factory.session() as s:
            user = s.get(self.model, id)
            if not user:
                return None
            # Eager load roles and convert to dict before closing session
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "roles": [{"id": str(r.id), "name": r.name} for r in user.roles],
            }
```

Service receives a plain dict:

```python
class UserService(SimpleService):
    def get_user(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user_dict = repo.get_with_roles(uuid.UUID(data["id"]))
        
        if not user_dict:
            raise ValueError(f"User {data['id']} not found")
        
        # No ORM, no session, no lazy-load errors — just a dict
        return user_dict
```

For complex objects, use Pydantic:

```python
from pydantic import BaseModel

class RoleSchema(BaseModel):
    id: str
    name: str

class UserSchema(BaseModel):
    id: str
    username: str
    email: str
    roles: list[RoleSchema]

class UserRepository(AbstractRepository[User]):
    model = User

    def get_with_roles(self, id) -> UserSchema | None:
        """Returns a validated Pydantic model."""
        with self._factory.session() as s:
            user = s.get(self.model, id)
            if not user:
                return None
            
            return UserSchema(
                id=str(user.id),
                username=user.username,
                email=user.email,
                roles=[RoleSchema(id=str(r.id), name=r.name) for r in user.roles],
            )
```

**Benefits**

- ✅ No lazy-load errors: all data fetched inside the session
- ✅ No session leaks: session closes immediately after query
- ✅ Safe: callers can't accidentally mutate the database
- ✅ Serializable: dicts and Pydantic models are JSON-safe
- ✅ Clear contracts: callers see exactly what data they get

---

### Anti-Pattern 7: Session Leaks in Repository Methods

**The Problem**

A repository opens a session but doesn't close it properly, or returns an object that still needs the session:

```python
# WRONG — session not properly managed
class UserRepository(AbstractRepository[User]):
    model = User

    def get_all(self) -> list[User]:
        """Returns ORM objects; session never closes explicitly."""
        s = self._factory.session()  # Session opened but never closed
        users = s.query(self.model).all()
        return users  # Session still open; will close eventually, but not managed

    def get_lazy(self, id) -> User:
        """Returns an ORM object that depends on the session."""
        s = self._factory.session()
        user = s.get(self.model, id)
        return user  # User's relationships will fail to load outside this session

    def get_no_context_manager(self, id) -> User | None:
        """Opens session without context manager — cleanup unreliable."""
        session = self._factory.session()
        try:
            obj = session.query(self.model).filter(self.model.id == id).first()
            return obj  # If exception happens after this, finally might not run
        finally:
            session.close()
```

**Why It Breaks**

1. **Resource leak**: Sessions pile up, connections exhaust
2. **Lazy-load errors**: Caller accesses relationships, session already closed
3. **Stale data**: Multiple callers read different snapshots
4. **Hard to debug**: Errors appear in caller code, not repository
5. **Unreliable cleanup**: `finally` blocks don't always run

**The Correct Way**

Use context managers (`with`) for all session access:

```python
# CORRECT — session managed with context manager
class UserRepository(AbstractRepository[User]):
    model = User

    def get(self, id) -> User | None:
        """Session opens, closes, and data is fetched before return.
        
        NOTE: This returns a raw ORM object. The SessionFactory has
        expire_on_commit=False, so scalar columns (id, username, email)
        are safe to access after the session closes. However, relationships
        (e.g., user.roles) will raise DetachedInstanceError. Convert to dict
        in _stage_impl if you access relationships outside this method.
        """
        with self._factory.session() as s:
            return s.get(self.model, id)

    def list(self, **filters) -> list[User]:
        """All users fetched inside the context."""
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)
            return q.all()  # List fully loaded before context closes

    def get_as_dict(self, id) -> dict | None:
        """Convert to dict before returning — no lazy loads outside."""
        with self._factory.session() as s:
            user = s.get(self.model, id)
            if not user:
                return None
            # Eagerly serialize before session closes
            return {"id": user.id, "username": user.username}
```

For complex relationships, eager-load inside the context:

```python
# Eager-load relationships to avoid lazy-load errors
from sqlalchemy.orm import joinedload

class UserRepository(AbstractRepository[User]):
    model = User

    def get_with_roles(self, id) -> User | None:
        """Eager-load roles so they're available outside the session."""
        with self._factory.session() as s:
            return s.query(self.model)\
                .options(joinedload(self.model.roles))\
                .filter(self.model.id == id)\
                .one_or_none()
```

Or return dicts to avoid ORM concerns:

```python
def get_with_roles_as_dict(self, id) -> dict | None:
    """Convert to dict inside the session — caller never sees ORM."""
    with self._factory.session() as s:
        user = s.get(self.model, id)
        if not user:
            return None
        return {
            "id": str(user.id),
            "username": user.username,
            "roles": [{"id": str(r.id), "name": r.name} for r in user.roles],
        }
```

**Benefits**

- ✅ No resource leaks: every session closes immediately
- ✅ No lazy-load errors: relationships loaded inside the session
- ✅ Predictable behavior: no hidden session state
- ✅ Easier debugging: errors happen in the repository, not the caller
- ✅ Safe concurrency: sessions are independent, don't interfere

---

### Anti-Pattern 8: Generic Filter Without Type Safety

**The Problem**

A repository uses `**filters` with `getattr()` for any column, no validation:

```python
# WRONG — unsafe filtering
class UserRepository(AbstractRepository[User]):
    model = User

    def list(self, **filters) -> list[User]:
        """Accept any column name as a filter — caller can request anything."""
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)  # Accepts invalid columns silently
            return q.all()

# Caller:
repo = UserRepository(factory)
users = repo.list(invalid_column="foo")  # Silently ignored — returns all users
users = repo.list(role_id="123")  # Works but ORM is confused — may return wrong data
users = repo.list(username="alice", extra="data")  # Extra data ignored
```

**Why It Breaks**

1. **Silent failures**: Invalid columns are silently ignored
2. **Inconsistent behavior**: Caller doesn't know what filters worked
3. **No validation**: Accepts `__dict__`, `__init__`, or other unsafe attributes
4. **Unclear contracts**: Repository doesn't document what's filterable
5. **Hard to debug**: Missing filter produces no error

**The Correct Way**

Define explicit filter methods with named parameters:

```python
# CORRECT — explicit, type-safe filters
class UserRepository(AbstractRepository[User]):
    model = User

    def get_by_username(self, username: str) -> User | None:
        """Find user by username."""
        with self._factory.session() as s:
            return s.query(self.model)\
                .filter(self.model.username == username)\
                .one_or_none()

    def list_by_role(self, role_name: str) -> list[User]:
        """List all users with a specific role."""
        with self._factory.session() as s:
            from lib.models.role import Role
            return s.query(self.model)\
                .join(Role, self.model.roles)\
                .filter(Role.name == role_name)\
                .all()

    def list_active(self, limit: int = 100) -> list[User]:
        """List active users (last_login within 30 days)."""
        from datetime import datetime, timedelta
        threshold = datetime.utcnow() - timedelta(days=30)
        
        with self._factory.session() as s:
            return s.query(self.model)\
                .filter(self.model.last_login > threshold)\
                .limit(limit)\
                .all()

    def list_all(self) -> list[User]:
        """List all users."""
        with self._factory.session() as s:
            return s.query(self.model).all()
```

Service calls named methods:

```python
class UserService(SimpleService):
    def find_by_username(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.get_by_username(data["username"])
        if not user:
            raise ValueError(f"User {data['username']} not found")
        return {"id": str(user.id), "username": user.username}

    def find_active(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        users = repo.list_active(limit=data.get("limit", 100))
        return {"users": [{"id": str(u.id), "username": u.username} for u in users]}
```

If you need dynamic filtering, validate the keys:

```python
# Only if necessary — validate against allowed columns
ALLOWED_FILTERS = {"username", "email", "is_active"}

class UserRepository(AbstractRepository[User]):
    model = User

    def list(self, **filters) -> list[User]:
        """List with validated filters only."""
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                if k not in ALLOWED_FILTERS:
                    raise ValueError(f"Invalid filter: {k}. Allowed: {ALLOWED_FILTERS}")
                q = q.filter(getattr(self.model, k) == v)
            return q.all()
```

**Benefits**

- ✅ Type safety: callers know exactly what filters exist
- ✅ Explicit contracts: documentation shows available methods
- ✅ Easy to optimize: can add indexes for common queries
- ✅ Predictable: no silent failures or unexpected behavior
- ✅ Maintainable: changes to queries happen in one place per method

---

## View Anti-Patterns

### Anti-Pattern 9: Views Importing Services Directly

**The Problem**

A view imports a service and creates an instance, instead of receiving it via props:

```python
# WRONG — view imports service directly
from lib.services.user_service import UserService
from lib.database.session import ConnectionRegistry
import flet as ft

class UserListView(BaseView):
    title = "Users"

    def __init__(self, page, props):
        super().__init__(page, props)
        # Create service directly — breaks dependency injection
        self._user_service = UserService(ConnectionRegistry.get())

    def build_content(self):
        users = self._user_service.list_users()
        return ft.Column([
            ft.Text(f"User: {u['username']}")
            for u in users
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return UserListView(page, props).render()
```

**Why It Breaks**

1. **Untestable**: Can't inject a mock service for testing
2. **Tight coupling**: View is tightly bound to `UserService` implementation
3. **Hidden dependencies**: Callers don't know the view needs a factory and service
4. **Configuration leak**: View has database configuration baked in
5. **Violates CONVENTIONS.md**: Rule explicitly forbids direct imports in views

**The Correct Way**

Services come via the `props` dict:

```python
# CORRECT — service injected via props
import flet as ft
from lib.ui.layouts.base_view import BaseView

class UserListView(BaseView):
    title = "Users"

    def build_content(self):
        user_service = self.props["user_service"]  # Injected by router
        result = user_service.execute(ActionRequest(action="list", data={}))
        
        if not result.success:
            return ft.Text(f"Error: {result.error}")
        
        users = result.data.get("users", [])
        return ft.Column([
            ft.Text(f"User: {u['username']}")
            for u in users
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return UserListView(page, props).render()
```

Wire the service in `main.py`:

```python
def main():
    factory = ConnectionRegistry.get()
    user_service = UserService(factory)
    
    router = FletRouter(nav_service, views_package="lib.views")
    router.set_props_factory(lambda: {
        "user_service": user_service,
        "role_service": role_service,
        "nav_service": nav_service,
    })
```

**Special case: Registries are OK to import**

`ConnectionRegistry` and `CacheRegistry` are global lookup tables, not stateful services:

```python
# OK — registries are read-only lookups
from lib.database.session import ConnectionRegistry
from lib.services.cache_registry import CacheRegistry

class SettingsView(BaseView):
    def build_content(self):
        available_dbs = ConnectionRegistry.list()  # Registry is a global lookup, not a service
        available_caches = CacheRegistry.list()
        
        return ft.Column([
            ft.Text(f"Database: {db}") for db in available_dbs
        ])
```

**Benefits**

- ✅ Testable: inject mock services in tests
- ✅ Flexible: swap services without touching view code
- ✅ Clear dependencies: props dict shows what the view needs
- ✅ Follows CONVENTIONS.md: aligns with framework rules
- ✅ Decoupled: view doesn't know about factories, sessions, or ORM

---

### Anti-Pattern 10: Direct HTTP Calls in Event Handlers

**The Problem**

A view makes HTTP calls directly inside button handlers, without error handling:

```python
# WRONG — direct HTTP call in handler, no error handling
import httpx
import flet as ft

class LoginView(BaseView):
    title = "Login"

    def build_content(self):
        username_field = ft.TextField(label="Username")
        password_field = ft.TextField(label="Password", password=True)
        
        def on_login(e):
            # Direct HTTP call — what if the server is down?
            response = httpx.post("http://localhost:8000/users/login", json={
                "username": username_field.value,
                "password": password_field.value,
            })
            # No error handling — if the request fails, the app crashes
            data = response.json()
            if data["success"]:
                # Hardcoded URL — can't swap backends
                self.nav_service.execute(ActionRequest(action="visit", data={
                    "url": "/dashboard",
                }))
        
        return ft.Column([
            username_field,
            password_field,
            ft.ElevatedButton("Login", on_click=on_login),
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return LoginView(page, props).render()
```

**Why It Breaks**

1. **No error handling**: Network errors crash the app
2. **Hardcoded URLs**: Can't change the API endpoint without code changes
3. **No retry logic**: Transient failures fail permanently
4. **Synchronous blocking**: UI freezes while the request waits
5. **Untestable**: Can't mock HTTP calls easily

**The Correct Way**

Use a service injected via props; it handles HTTP, errors, and retries:

```python
# CORRECT — service handles HTTP
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest

class LoginView(BaseView):
    title = "Login"

    def build_content(self):
        username_field = ft.TextField(label="Username")
        password_field = ft.TextField(label="Password", password=True)
        error_text = ft.Text(color="red")
        
        def on_login(e):
            # Service handles all HTTP concerns
            login_service = self.props["login_service"]
            result = login_service.execute(ActionRequest(action="login", data={
                "username": username_field.value,
                "password": password_field.value,
            }))
            
            if result.success:
                self.nav_service.execute(ActionRequest(action="visit", data={
                    "url": "/dashboard",
                }))
            else:
                error_text.value = f"Login failed: {result.error}"
                self.page.update()
        
        return ft.Column([
            username_field,
            password_field,
            ft.ElevatedButton("Login", on_click=on_login),
            error_text,
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return LoginView(page, props).render()
```

Service handles HTTP and errors:

```python
import httpx
from lib.core.interfaces import SimpleService

class LoginService(SimpleService):
    def __init__(self, api_url: str = "http://localhost:8000"):
        self._api_url = api_url

    def login(self, data: dict) -> dict:
        """Login via HTTP API."""
        try:
            response = httpx.post(f"{self._api_url}/users/login", json=data, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise RuntimeError("Login request timed out")
        except httpx.HTTPError as e:
            raise RuntimeError(f"Login failed: {e}")
```

For async operations, use threading to avoid blocking:

```python
# If the service is truly asynchronous, wrap it
import threading
from lib.core.interfaces import SimpleService

class AsyncLoginView(BaseView):
    title = "Login"

    def build_content(self):
        username_field = ft.TextField(label="Username")
        password_field = ft.TextField(label="Password", password=True)
        status_text = ft.Text()
        
        def on_login(e):
            login_service = self.props["login_service"]
            status_text.value = "Logging in..."
            self.page.update()
            
            def do_login():
                result = login_service.execute(ActionRequest(action="login", data={
                    "username": username_field.value,
                    "password": password_field.value,
                }))
                
                # Update UI on main thread
                if result.success:
                    self.nav_service.execute(ActionRequest(action="visit", data={"url": "/dashboard"}))
                else:
                    status_text.value = f"Login failed: {result.error}"
                    self.page.update()
            
            # Run in background thread so UI doesn't freeze
            threading.Thread(target=do_login, daemon=True).start()
        
        return ft.Column([
            username_field,
            password_field,
            ft.ElevatedButton("Login", on_click=on_login),
            status_text,
        ])
```

**Benefits**

- ✅ Error handling: service catches network errors gracefully
- ✅ Configurable: API URL is configurable, not hardcoded
- ✅ Retry logic: service can implement retries, backoff, etc.
- ✅ Non-blocking: background threads prevent UI freezes
- ✅ Testable: mock the service, not HTTP

---

### Anti-Pattern 11: Event Handlers Without Try/Except

**The Problem**

An event handler has no error handling, so exceptions crash the app:

```python
# WRONG — no error handling in handlers
import flet as ft

class OrderView(BaseView):
    title = "Orders"

    def build_content(self):
        quantity_field = ft.TextField(label="Quantity")
        
        def on_create_order(e):
            # No try/except — if this raises, the app crashes
            order_service = self.props["order_service"]
            quantity = int(quantity_field.value)  # ValueError if not a number
            
            result = order_service.execute(ActionRequest(action="create", data={
                "quantity": quantity,
            }))
            
            # No check for result.success — assumption is it always works
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Order created: {result.data['order_id']}")
            )
            self.page.snack_bar.open = True
            self.page.update()
        
        return ft.Column([
            quantity_field,
            ft.ElevatedButton("Create Order", on_click=on_create_order),
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return OrderView(page, props).render()
```

**Why It Breaks**

1. **App crashes**: Any unhandled exception closes the UI
2. **No user feedback**: Users don't know what went wrong
3. **Silent failures**: Errors in logs, not visible to user
4. **Poor UX**: App seems broken, not responsive

**The Correct Way**

Wrap handlers in try/except and show error messages:

```python
# CORRECT — error handling with user feedback
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest

class OrderView(BaseView):
    title = "Orders"

    def build_content(self):
        quantity_field = ft.TextField(label="Quantity")
        error_banner = ft.Banner(
            content=ft.Text(""),  # Use content=, not title=
            leading=ft.Icon(ft.Icons.ERROR),  # Use ft.Icons (capital I)
            bgcolor="#ffebee",
        )
        
        def on_create_order(e):
            try:
                # Validate input
                if not quantity_field.value:
                    raise ValueError("Quantity is required")
                
                try:
                    quantity = int(quantity_field.value)
                except ValueError:
                    raise ValueError("Quantity must be a number")
                
                if quantity <= 0:
                    raise ValueError("Quantity must be positive")
                
                # Call service
                order_service = self.props["order_service"]
                result = order_service.execute(ActionRequest(action="create", data={
                    "quantity": quantity,
                }))
                
                # Check result
                if not result.success:
                    raise RuntimeError(result.error)
                
                # Show success
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Order created: {result.data['order_id']}")
                )
                self.page.snack_bar.open = True
                quantity_field.value = ""
                self.page.update()
                
            except Exception as exc:
                # Show error to user
                error_banner.content.value = f"Error: {exc}"  # Access content, not title
                error_banner.open = True
                self.page.update()
        
        return ft.Column([
            error_banner,
            quantity_field,
            ft.ElevatedButton("Create Order", on_click=on_create_order),
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return OrderView(page, props).render()
```

For reusable error handling, create a helper:

```python
# Helper for consistent error handling
def handle_action_error(page: ft.Page, exc: Exception, on_error_fn=None):
    """Show error message and optionally log."""
    message = str(exc)
    print(f"[ERROR] {message}")
    
    page.snack_bar = ft.SnackBar(ft.Text(f"Error: {message}"))
    page.snack_bar.open = True
    page.update()
    
    if on_error_fn:
        on_error_fn(exc)

# Then use it in handlers:
def on_create_order(e):
    try:
        order_service = self.props["order_service"]
        # ... logic ...
    except Exception as exc:
        handle_action_error(self.page, exc)
```

**Benefits**

- ✅ App stability: exceptions don't crash the UI
- ✅ User feedback: users see what went wrong
- ✅ Graceful degradation: app keeps working
- ✅ Debuggable: errors are logged, not hidden

---

### Anti-Pattern 12: Mixing Sync and Async Without Clear Boundaries

**The Problem**

A view mixes synchronous and asynchronous operations without clear boundaries:

```python
# WRONG — unclear async/sync boundaries
import flet as ft
import httpx
import asyncio

class DataView(BaseView):
    title = "Data"

    def build_content(self):
        async def fetch_data():
            # Async function but called from sync handler
            response = await httpx.AsyncClient().get("http://localhost:8000/data")
            return response.json()

        def on_fetch(e):
            # Calling async from sync — requires event loop juggling
            try:
                # This doesn't work correctly in Flet
                data = asyncio.run(fetch_data())
                self.page.update()
            except Exception as exc:
                print(f"Error: {exc}")

        return ft.Column([
            ft.ElevatedButton("Fetch Data", on_click=on_fetch),
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return DataView(page, props).render()
```

**Why It Breaks**

1. **Event loop conflicts**: Flet has its own event loop; `asyncio.run()` conflicts
2. **UI freezes**: Async operations block the main thread
3. **Error handling is unclear**: Exceptions in async code are hard to catch
4. **Untestable**: Mixing async/sync makes testing complex

**The Correct Way**

Use services; they handle async internally if needed. The view stays synchronous:

```python
# CORRECT — service handles async/sync complexity
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest
import threading

class DataView(BaseView):
    title = "Data"

    def build_content(self):
        data_text = ft.Text("Click button to fetch...")
        status_text = ft.Text()
        
        def on_fetch(e):
            data_service = self.props["data_service"]
            status_text.value = "Loading..."
            self.page.update()
            
            # Run in background thread — service is still synchronous
            def do_fetch():
                try:
                    result = data_service.execute(ActionRequest(action="fetch", data={}))
                    if result.success:
                        data_text.value = str(result.data)
                    else:
                        data_text.value = f"Error: {result.error}"
                finally:
                    status_text.value = ""
                    self.page.update()
            
            threading.Thread(target=do_fetch, daemon=True).start()
        
        return ft.Column([
            data_text,
            status_text,
            ft.ElevatedButton("Fetch Data", on_click=on_fetch),
        ])

def view(page: ft.Page, props: dict) -> ft.View:
    return DataView(page, props).render()
```

Service handles async internally:

```python
import httpx
from lib.core.interfaces import SimpleService

class DataService(SimpleService):
    def __init__(self, api_url: str = "http://localhost:8000"):
        self._api_url = api_url

    def fetch(self, data: dict) -> dict:
        """Fetch data from API (synchronous from caller's perspective)."""
        try:
            # Service uses synchronous httpx
            response = httpx.get(f"{self._api_url}/data", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch data: {e}")
```

**Benefits**

- ✅ Clear boundaries: views stay synchronous, services handle complexity
- ✅ No event loop conflicts: threading used instead of asyncio
- ✅ Testable: mocking is straightforward
- ✅ Maintainable: UI code is simple and readable
- ✅ Non-blocking: background threads prevent freezes

---

## Container & Wiring Anti-Patterns

### Anti-Pattern 13: Service Imports Service (In Initialization)

**The Problem**

One service imports and instantiates another service directly, instead of receiving it:

```python
# WRONG — service imports service
from lib.services.user_service import UserService
from lib.services.email_service import EmailService
from lib.core.interfaces import SimpleService

class OnboardingService(SimpleService):
    def __init__(self, factory):
        self._factory = factory
        # Hardcoded import and instantiation
        self._user_service = UserService(factory)
        self._email_service = EmailService()

    def onboard_user(self, data: dict) -> dict:
        user_result = self._user_service.execute(ActionRequest(
            action="create", data=data
        ))
        # ...rest of logic
```

**Why It Breaks**

1. **Dependency injection broken**: `OnboardingService` can't receive a mock `EmailService`
2. **Initialization order matters**: If `EmailService` depends on `UserService`, we have a problem
3. **Testing fails**: Can't test `OnboardingService` with a test email service
4. **Hidden dependencies**: Callers don't know `OnboardingService` needs `EmailService`
5. **Circular imports possible**: If `EmailService` imports something from `OnboardingService`

**The Correct Way**

Inject the dependencies explicitly:

```python
# CORRECT — all dependencies injected
from lib.core.interfaces import SimpleService
from lib.contracts.base import ActionRequest

class OnboardingService(SimpleService):
    def __init__(self, factory, user_service: UserService, email_service: EmailService):
        self._factory = factory
        self._user_service = user_service
        self._email_service = email_service

    def onboard_user(self, data: dict) -> dict:
        user_result = self._user_service.execute(ActionRequest(
            action="create", data=data
        ))
        if not user_result.success:
            raise ValueError(user_result.error)
        
        email_result = self._email_service.execute(ActionRequest(
            action="send_welcome", data={
                "user_id": user_result.data["id"],
                "email": data["email"],
            }
        ))
        
        return {
            "user_id": user_result.data["id"],
            "email_sent": email_result.success,
        }
```

Wire in `main.py`:

```python
def main():
    factory = ConnectionRegistry.get()
    
    # Create services in dependency order
    user_service = UserService(factory)
    email_service = EmailService()  # No dependencies
    onboarding_service = OnboardingService(factory, user_service, email_service)
    
    # Now all dependencies are explicit and testable
    api_app = FastAPI()
    mount_routes(api_app, {
        "onboarding": onboarding_service,
    })
```

For unit tests:

```python
# Test with mocks
class MockEmailService:
    def execute(self, request):
        return ActionResult(success=True, data={"sent": True})

def test_onboarding():
    factory = create_test_factory()
    user_service = UserService(factory)
    email_service = MockEmailService()  # Inject test mock
    onboarding_service = OnboardingService(factory, user_service, email_service)
    
    result = onboarding_service.execute(ActionRequest(
        action="onboard_user",
        data={"username": "alice", "email": "alice@example.com"}
    ))
    
    assert result.success
```

**Benefits**

- ✅ Testable: inject mocks for all dependencies
- ✅ Explicit: dependencies are clear in `__init__`
- ✅ Flexible: swap implementations without code changes
- ✅ No circular imports: each service only imports contracts
- ✅ Clear initialization order: `main.py` shows the full dependency graph

---

### Anti-Pattern 14: Multiple Containers / Factories

**The Problem**

Different parts of the code create different service instances or factories:

```python
# WRONG — multiple service instances
from lib.database.session import SessionFactory
from lib.services.user_service import UserService

# In main.py
def main():
    factory = SessionFactory()
    user_service1 = UserService(factory)
    # ... pass to router

# In a routes file
from lib.database.session import SessionFactory
from lib.services.user_service import UserService

def get_user_service():
    factory = SessionFactory()  # Creates a DIFFERENT factory
    return UserService(factory)  # Different instance

# In a view
from lib.services.user_service import UserService
from lib.database.session import SessionFactory

user_service2 = UserService(SessionFactory())  # Yet another instance
```

**Why It Breaks**

1. **No singleton pattern**: Each service has a different session pool
2. **Wasted resources**: Multiple database pools open simultaneously
3. **Stale data**: Different instances see different cached data
4. **Transaction isolation**: Changes in one service don't affect another
5. **Hard to debug**: Mysterious data inconsistencies

**The Correct Way**

Create all services once in `main.py` and share them everywhere:

```python
# CORRECT — single source of truth
def main():
    # Create once, share everywhere
    factory = SessionFactory("sqlite:///app.db")  # Provide required URL
    
    user_service = UserService(factory)
    role_service = RoleService(factory)
    email_service = EmailService()
    
    # Pass to router
    router = FletRouter(nav_service, views_package="lib.views")
    router.set_props_factory(lambda: {
        "factory": factory,
        "user_service": user_service,
        "role_service": role_service,
        "email_service": email_service,
    })
    
    # Pass to API
    api_app = FastAPI()
    
    def get_services():
        return {
            "user": user_service,
            "role": role_service,
            "email": email_service,
        }
    
    mount_routes(api_app, get_services())
```

No service creates its own factory:

```python
# In routes/users.py — uses the shared factory
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users")

_user_service = None  # Set by main.py

def set_user_service(service):
    global _user_service
    _user_service = service

@router.post("")
def create_user(data: dict):
    result = _user_service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

Or better yet, use dependency injection in FastAPI:

```python
# Using FastAPI's Depends for cleaner injection
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users")

def get_user_service() -> UserService:
    # This comes from main.py; FastAPI manages the injection
    return app.state.user_service

@router.post("")
def create_user(data: dict, service: UserService = Depends(get_user_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

In `main.py`:

```python
def main():
    factory = SessionFactory("sqlite:///app.db")  # Provide required URL
    user_service = UserService(factory)
    
    api_app = FastAPI()
    api_app.state.factory = factory
    api_app.state.user_service = user_service
    
    mount_routes(api_app)
```

**Benefits**

- ✅ Single source of truth: one factory, one set of services
- ✅ Resource efficiency: database pool is shared, not duplicated
- ✅ Consistent data: all services read from the same cache
- ✅ Easy testing: swap in test services globally
- ✅ Clear wiring: `main.py` shows the complete dependency graph

---

### Anti-Pattern 15: Mixing Test Mocks with Production Code

**The Problem**

Production code includes branches for testing, or imports test fixtures:

```python
# WRONG — test mocks in production
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory

class UserService(SimpleService):
    def __init__(self, factory: SessionFactory, use_test_mode: bool = False):
        self._factory = factory
        self._use_test_mode = use_test_mode  # Test mode flag in production

    def create(self, data: dict) -> dict:
        if self._use_test_mode:
            # Test logic mixed with production
            return {"id": "test-123", "username": "test_user"}
        
        repo = UserRepository(self._factory)
        user = repo.create(data)
        return {"id": str(user.id), "username": user.username}

# Or worse: importing test helpers
try:
    from lib.tests.fixtures import mock_factory  # Test code in imports
except ImportError:
    mock_factory = None

# Usage:
factory = mock_factory if mock_factory else SessionFactory()
service = UserService(factory)
```

**Why It Breaks**

1. **Production contains test code**: Larger binary, harder to maintain
2. **Branches never tested**: Test branches aren't exercised in production
3. **Accidental test mode in production**: If someone sets the flag, behavior changes
4. **Import errors from test modules**: If test fixtures change, production breaks
5. **Security risk**: Test mocks might expose or skip security checks

**The Correct Way**

Keep test code completely separate; never branch on test mode:

```python
# CORRECT — clean separation
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory

class UserService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory
        # No test mode flag; production code is clean

    def create(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.create(data)
        return {"id": str(user.id), "username": user.username}
```

Test code is completely separate:

```python
# In tests/services/test_user_service.py
import pytest
from unittest.mock import patch
from lib.services.user_service import UserService
from lib.contracts.base import ActionRequest

class MockUserRepository:
    """Test double — not in production."""
    def create(self, data):
        class MockUser:
            id = "test-123"
            username = data["username"]
        return MockUser()

def test_user_service_create():
    """Test without touching production code."""
    class MockFactory:
        pass
    
    service = UserService(MockFactory())
    
    # Use unittest.mock.patch() — properly rebinds the module namespace
    with patch("lib.services.user_service.UserRepository", MockUserRepository):
        result = service.execute(ActionRequest(
            action="create",
            data={"username": "alice"}
        ))
        assert result.success
        assert result.data["username"] == "alice"
```

Or better yet, use a test factory that creates real services with a test database:

```python
# In tests/conftest.py
import pytest
from lib.database.session import SessionFactory
from lib.services.user_service import UserService

@pytest.fixture
def test_db_factory():
    """Create a real in-memory database for testing."""
    factory = SessionFactory(url="sqlite:///:memory:")
    # Create all tables
    from lib.models.base import DeclarativeBase
    with factory.session() as s:
        DeclarativeBase.metadata.create_all(s.connection())
    return factory

@pytest.fixture
def user_service(test_db_factory):
    """Service with real database, but test data."""
    return UserService(test_db_factory)

def test_user_service_create(user_service):
    """Test with real service and test database."""
    result = user_service.execute(ActionRequest(
        action="create",
        data={"username": "alice", "email": "alice@example.com"}
    ))
    assert result.success
```

**Benefits**

- ✅ Clean separation: test code is completely isolated
- ✅ Smaller production binary: no unused test branches
- ✅ Simpler logic: no branching, less to reason about
- ✅ More confidence: only production code is shipped
- ✅ Better testing: can test with real services and test databases

---

## Summary: The Right Way

| Layer | Anti-Pattern | The Right Way |
|---|---|---|
| **Services** | Hardcoded imports | Dependency injection in `__init__` |
| **Services** | Service calling service | Inject the service, or use `StagingService` |
| **Services** | Direct ORM access | Always use repositories |
| **Services** | ActionRequest chains | Call methods directly within the service |
| **Services** | Query logic in methods | Move to repository-specific methods |
| **Repositories** | Returning raw ORM | Return dicts or Pydantic models |
| **Repositories** | Session leaks | Use `with` context managers always |
| **Repositories** | Generic `**filters` | Define explicit filter methods |
| **Views** | Importing services | Receive via `props` dict |
| **Views** | Direct HTTP calls | Use injected services |
| **Views** | No error handling | Wrap handlers in try/except |
| **Views** | Async/sync mixing | Keep views synchronous; services handle complexity |
| **Wiring** | Service imports service | Inject at construction time |
| **Wiring** | Multiple factories | Create once in `main.py`, share everywhere |
| **Wiring** | Test mocks in production | Keep tests completely separate |

---

## Cross-References

- [CONVENTIONS.md](CONVENTIONS.md) — Rules for naming, structure, imports, and docstrings
- [ARCHITECTURE.md](ARCHITECTURE.md) — System overview and design decisions
- [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) — `ActionRequest` and `ActionResult` contracts
- [API_PATTERN_TEMPLATE.md](API_PATTERN_TEMPLATE.md) — How to add new API endpoints
- [TESTING.md](TESTING.md) — Testing strategies that depend on these patterns

