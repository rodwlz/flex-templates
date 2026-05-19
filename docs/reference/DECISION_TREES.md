---
title: "Decision Trees: When to Use Which Pattern"
category: reference
audience: [developer, agent]
related:
  - ../core/CONVENTIONS.md
  - ../guides/API_DEVELOPMENT.md
  - ../guides/VIEW_DEVELOPMENT.md
agent_priority: medium
---

# FlexTemplates 2.0 — Decision Trees

Pattern selection guide. Answers the five questions developers ask most often.

---

## Quick Reference Table

| Question | Answer |
|---|---|
| Should my service extend `SimpleService` or `StagingService`? | One-shot operations → `SimpleService`. Operations that span a transaction and benefit from a preview diff → `StagingService`. |
| Should this endpoint be immediate, staged, or approval-required? | No side-effects to preview → immediate. Complex transaction user should review before commit → staged. Destructive / irreversible → approval. |
| Should I emit an `Event`? | Other parts of the app need to react (UI, adapter, another service) → yes. Caller already holds the result and no other layer cares → no. |
| Should I create a new service or add a method to an existing one? | Different repository (different ORM model) → new service. Same data domain → add a method. |
| Should this be a `SimpleService` or a custom `execute()` with `match`? | Default → `SimpleService`. Action names collide with properties, or every branch returns custom `events=[...]` → custom `execute()`. |

Jump to any section:

- [Tree 1 — SimpleService vs StagingService](#tree-1--simpleservice-vs-stagingservice)
- [Tree 2 — Immediate vs Staged vs Approval endpoints](#tree-2--immediate-vs-staged-vs-approval-endpoints)
- [Tree 3 — When to emit an Event](#tree-3--when-to-emit-an-event)
- [Tree 4 — New service vs new method](#tree-4--new-service-vs-new-method)
- [Tree 5 — SimpleService vs custom execute()](#tree-5--simpleservice-vs-custom-execute)

---

## Tree 1 — SimpleService vs StagingService

```
Does the operation touch more than one repository table
in a way that needs to be atomic and previewed before commit?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                             Use StagingService.
         │                                                    Implement _stage_impl().
         │                                                    Add stage/confirm/cancel
         │                                                    methods automatically.
         ▼
Does the operation simply read or write one record / one table?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                              Use SimpleService.
         │                                                    One public method per action.
         │                                                    Exceptions auto-trapped.
         ▼
Does the operation write one record but also modify a relationship
(many-to-many join table)?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                   Use StagingService when the
         │                                                   user needs a preview before
         ▼                                                   the join table is committed.
  Use SimpleService.                                         Use SimpleService when the
  No preview needed.                                         relationship is a detail the
                                                            caller handles directly.
```

### Example — SimpleService: RoleService

`Role` has no relationships. Every operation is one query. Use `SimpleService`.

```python
# lib/services/role_service.py
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory
from lib.repositories.role_repository import RoleRepository
import uuid

class RoleService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def create(self, data: dict) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.create(data)
        return {"id": str(role.id), "name": role.name}

    def delete(self, data: dict) -> dict:
        repo = RoleRepository(self._factory)
        deleted = repo.delete(uuid.UUID(data["id"]))
        if not deleted:
            raise ValueError(f"Role {data['id']} not found")
        return {"deleted": True}
```

`SimpleService` dispatches `ActionRequest.action` to the matching method name automatically. Raising a `ValueError` inside any method becomes `ActionResult(success=False, error="Role ... not found")` — no try/except needed.

### Example — StagingService: UserService

Creating a `User` with roles touches two tables atomically (`users` + `user_roles`). The caller needs to see what will be written before committing. Use `StagingService`.

```python
# lib/services/user_service.py
from lib.core.interfaces import StagingService
from lib.database.session import SessionFactory
from lib.repositories.user_repository import UserRepository
from lib.repositories.role_repository import RoleRepository
import uuid

class UserService(StagingService):
    def __init__(self, factory: SessionFactory):
        super().__init__(factory)

    # Immediate operations still work — defined as plain methods
    def get(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.get(uuid.UUID(data["id"]))
        if user is None:
            raise ValueError(f"User {data['id']} not found")
        return {"id": str(user.id), "username": user.username, "roles": [r.name for r in user.roles]}

    # Staged operation — override _stage_impl, not stage()
    def _stage_impl(self, uow, data: dict) -> dict:
        repo = uow.repo(UserRepository)
        role_repo = uow.repo(RoleRepository)
        user = repo.create({"username": data["username"], "email": data["email"], "password_hash": "", "salt": ""})
        for role_id in data.get("role_ids", []):
            role = role_repo.get(uuid.UUID(role_id) if isinstance(role_id, str) else role_id)
            if role:
                user.roles.append(role)
        return {"user_id": str(user.id), "role_count": len(user.roles)}
```

Calling `service.execute(ActionRequest(action="stage", data={...}))` opens a unit-of-work and runs `_stage_impl`. The transaction stays open. Calling `confirm` commits; calling `cancel` rolls back.

**Rule of thumb:** If you find yourself writing `with session:` and making multiple `repo.create()` calls inside a single service method, that is a staged operation.

---

## Tree 2 — Immediate vs Staged vs Approval endpoints

```
Is the HTTP operation a simple read (GET)?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                          Immediate endpoint.
         │                                                          GET /resource/{id}
         ▼
Does the operation change the database in a way that could be
previewed before commit (e.g. creates records across multiple tables)?
         │
        NO ───────────────────────────────────────────────────────────────────►
         │                                                                     │
        YES                                                        Immediate endpoint.
         │                                                         POST /resource
         ▼                                                         DELETE /resource/{id}
Is the operation destructive, irreversible, or a bulk change
that carries significant risk if made in error?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                          Approval-required.
         │                                                          POST /resource/action/request
         ▼                                                          POST /resource/action/approve
Staged endpoint.
POST /resource/with-{detail}/stage
POST /resource/with-{detail}/confirm
POST /resource/with-{detail}/cancel
```

### Example — Immediate: roles.py

`Role` is a simple record. No relationships, no risk of partial writes. All four endpoints are immediate.

```python
# lib/api/routes/roles.py
@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data

@router.delete("/{role_id}")
def delete_role(role_id: str, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="delete", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data
```

### Example — Staged: POST /users/with-roles/stage + confirm + cancel

Creating a `User` with roles must be atomic — either both the user row and the `user_roles` rows land together, or neither does. The client previews the diff before committing.

```python
# lib/api/routes/users.py (staged section)
@router.post("/with-roles/stage", tags=["staged"])
def stage_user_with_roles(data: dict, service: UserService = Depends(get_service)):
    """Stage creation of a user with roles. Returns a preview diff."""
    result = service.execute(ActionRequest(action="stage", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data

@router.post("/with-roles/confirm", tags=["staged"])
def confirm_user_with_roles(service: UserService = Depends(get_service)):
    """Commit the staged user-with-roles creation."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data

@router.post("/with-roles/cancel", tags=["staged"])
def cancel_user_with_roles(service: UserService = Depends(get_service)):
    """Roll back the staged user-with-roles creation."""
    result = service.execute(ActionRequest(action="cancel", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

Note the service cache: `UserService` keeps the in-flight unit-of-work in `self._pending` between the `stage` and `confirm` calls. A fresh service instance per request would lose that state. Route files that use `StagingService` use a module-level `_service_cache` keyed by the factory identity.

### Example — Approval: POST /users/bulk-delete/request + approve

Deleting many users is irreversible. The `requires_approval=True` flag on the `ActionRequest` signals to the client that an explicit confirmation step is mandatory before the data is gone.

```python
# lib/api/routes/users.py (approval section)
@router.post("/bulk-delete/request", tags=["approval"])
def request_bulk_delete(data: dict, service: UserService = Depends(get_service)):
    """Stage a bulk delete — preview only, does NOT commit."""
    request = ActionRequest(action="stage", data=data, requires_approval=True)
    result = service.execute(request)
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data

@router.post("/bulk-delete/approve", tags=["approval"])
def approve_bulk_delete(data: dict, service: UserService = Depends(get_service)):
    """Approve and commit the previously staged bulk delete."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

`requires_approval=True` does not change how `StagingService` processes the request at the framework level — it is a signal for client code and policy layers to enforce a second explicit step before calling `confirm`.

**Endpoint naming convention:**

| Operation type | URL shape | Tags |
|---|---|---|
| Immediate | `POST /resource`, `GET /resource/{id}`, `DELETE /resource/{id}` | `["immediate"]` |
| Staged | `POST /resource/with-{detail}/stage`, `.../confirm`, `.../cancel` | `["staged"]` |
| Approval | `POST /resource/action/request`, `.../approve` | `["approval"]` |

---

## Tree 3 — When to emit an Event

```
After this operation completes, does any other part of the application
need to react — without the caller explicitly notifying it?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                           Emit an Event.
         │                                                    event_bus.publish(Event(
         ▼                                                      type="entity.verb",
Is the caller itself going to read the result from ActionResult.data           payload={...}))
and update whatever needs updating?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                       Return ActionResult only.
         │                                                       No event needed.
         ▼
Is this a side effect that could recur from many places
(multiple services, multiple routes, multiple views)?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                           Emit an Event.
         │                                                    Centralise the reaction in
         ▼                                                    one subscriber rather than
  Return ActionResult only.                                  repeating the logic everywhere.
  Direct return is enough.
```

### Example — Emit: NavigationService publishes nav.route_changed

`NavigationService` has no knowledge of Flet. When a route changes, it cannot call `page.go()` directly — that would couple the service to the UI layer. Instead it emits an event; `FletNavigationAdapter` subscribes and calls `page.go()`.

```python
# lib/services/navigation_service.py (simplified)
from lib.contracts.base import ActionResult, Event

class NavigationService(IService):
    def _visit(self, url: str) -> ActionResult:
        self._history.append(url)
        self._current = url
        # Other parts of the app need to react — emit rather than call them directly
        self._event_bus.publish(Event(
            type="nav.route_changed",
            payload={"url": url, "can_go_back": len(self._history) > 1}
        ))
        return ActionResult(success=True, data=self._nav_state())
```

```python
# lib/ui/adapter.py — the subscriber
class FletNavigationAdapter:
    def __init__(self, navigation_service):
        navigation_service._event_bus.subscribe("nav.route_changed", self._on_route_changed)

    def bind_page(self, page):
        self.page = page

    def _on_route_changed(self, event: Event):
        self.page.go(event.payload["url"])
```

`NavigationService` and `FletNavigationAdapter` are fully decoupled. Swapping the Flet UI for a web frontend means replacing only `FletNavigationAdapter`, not touching `NavigationService`.

### Example — No event: RoleService.delete returns ActionResult directly

When a role is deleted, the caller (the API route) already has the result and displays it immediately. No other layer needs to react asynchronously. Emitting an event here would add noise with no subscriber.

```python
# lib/services/role_service.py
def delete(self, data: dict) -> dict:
    repo = RoleRepository(self._factory)
    deleted = repo.delete(uuid.UUID(data["id"]))
    if not deleted:
        raise ValueError(f"Role {data['id']} not found")
    # Caller holds the result. No other layer cares. No event needed.
    return {"deleted": True}
```

### Event naming convention

Events use `entity.verb` dot-notation: `user.created`, `nav.route_changed`, `cache.disconnected`. The payload carries whatever subscribers need — the `id` of the affected record is usually enough.

---

## Tree 4 — New service vs new method

```
Does the new behaviour read from or write to a different ORM model
than the models the existing service already uses?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                           Create a new service.
         │                                                    lib/services/<domain>_service.py
         ▼                                                    lib/repositories/<model>_repository.py
Does the new behaviour belong to the same conceptual domain
as an existing service?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                      Add a method to the
         │                                                       existing service.
         ▼                                                  Keep one method per action.
  Create a new service.
  The fact that it does not share a repository is enough
  to justify a separate class.
```

### Example — Add a method: UserService gains list_by_role

`list_by_role` queries the `User` table via `UserRepository`, which `UserService` already owns. The behaviour is still about users. Add a method.

```python
# lib/services/user_service.py — new method added
def list_by_role(self, data: dict) -> dict:
    """Return all users that carry a given role name."""
    repo = UserRepository(self._factory)
    users = repo.list_by_role(data["role_name"])
    return {
        "users": [{"id": str(u.id), "username": u.username} for u in users]
    }
```

No new file. No new class. The action is called via `service.execute(ActionRequest(action="list_by_role", data={"role_name": "admin"}))` and `SimpleService` dispatches it automatically.

### Example — New service: OrderService for a new Order model

Orders live in an `orders` table, served by `OrderRepository`. They are a different conceptual domain from users. Create `OrderService`.

```python
# lib/services/order_service.py — new file, new service
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory
from lib.repositories.order_repository import OrderRepository
import uuid

class OrderService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def create(self, data: dict) -> dict:
        repo = OrderRepository(self._factory)
        order = repo.create(data)
        return {"id": str(order.id), "status": order.status}

    def list(self, data: dict) -> dict:
        repo = OrderRepository(self._factory)
        return {"orders": [{"id": str(o.id)} for o in repo.list()]}
```

Wire it in `container.py` and drop `lib/api/routes/orders.py` — the router auto-discovers it.

### Boundary rules

| Indicator | Decision |
|---|---|
| New ORM model (`lib/models/*.py`) | New service + new repository |
| New query on an existing model | New method on existing repository |
| New business action on existing records | New method on existing service |
| Business action that spans two existing models | Decide by primary domain; the service can instantiate both repositories |

See [CONVENTIONS.md §5](../core/CONVENTIONS.md) for the full module placement rules and [CONVENTIONS.md §6](../core/CONVENTIONS.md) for import boundaries.

---

## Tree 5 — SimpleService vs custom execute()

```
Do any of the action names you need to define collide with
existing Python properties or attributes on the class?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                       Use custom execute() with match.
         │                                                    SimpleService resolves action names
         ▼                                                    via getattr — a property named
Does every action need to return an ActionResult with              "current" would shadow the
a custom events=[...] list rather than a plain dict?              action method.
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                       Use custom execute() with match.
         │                                                    The dict-auto-wrap shortcut
         ▼                                                    adds no value when every branch
Do any actions require argument coercion or default-injection      already constructs ActionResult.
before dispatch (e.g. int(data.get("steps", 1)))?
         │
        YES ──────────────────────────────────────────────────────────────────►
         │                                                                     │
        NO                                                       Use custom execute() with match.
         │                                                    Coercion before dispatch is not
         ▼                                                    expressible in a SimpleService method.
  Use SimpleService.
  One public method per action name. Plain dict returns.
  Exceptions auto-trapped. This is the right choice
  for 90 % of services.
```

### Example — SimpleService: RoleService (default choice)

No property collisions. No custom events. No argument coercion. Use `SimpleService`.

```python
# lib/services/role_service.py
class RoleService(SimpleService):
    def create(self, data: dict) -> dict:
        ...                     # return a plain dict — auto-wrapped
    def get(self, data: dict) -> dict:
        ...
    def list(self, data: dict) -> dict:
        ...
    def delete(self, data: dict) -> dict:
        ...
```

Calling `service.execute(ActionRequest(action="list", data={}))` routes to `list()` automatically. No `execute()` needed.

### Example — Custom execute(): NavigationService

`NavigationService` exposes `nav.current` as a Python property (returns the current URL for direct reads). `SimpleService` resolves action names with `getattr` — `getattr(self, "current")` returns the property value (a string), not a callable, which breaks dispatch.

Additionally, every branch returns `ActionResult` with `events=[...]` directly, and several actions need `int(data.get("steps", 1))` coercion. All three reasons apply: use a custom `execute()`.

```python
# lib/services/navigation_service.py (simplified)
from lib.contracts.base import ActionRequest, ActionResult, Event
from lib.core.interfaces import IService

class NavigationService(IService):
    @property
    def current(self) -> str:          # property — would collide with SimpleService dispatch
        return self._current

    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "visit":
                return self._visit(request.data["url"])
            case "back":
                steps = int(request.data.get("steps", 1))   # coercion before dispatch
                return self._back(steps)
            case "current":
                return ActionResult(success=True, data=self._nav_state())
            case _:
                return ActionResult(success=False, error=f"Unknown action: {request.action}")
```

Do not refactor `NavigationService` or `VaultService` to `SimpleService` — they hit all three reasons above intentionally.

### Decision summary

| Use `SimpleService` when… | Use custom `execute()` when… |
|---|---|
| Each action is an independent self-contained method | An action name collides with a class property |
| Return values are plain dicts (auto-wrapped) | Every branch builds `ActionResult` with custom `events` |
| No argument coercion or merging needed before dispatch | Arguments need coercion or defaulting before dispatch |
| ~90 % of new services | `NavigationService`, `VaultService`, and similar edge cases |

---

## Cross-references

| Topic | Docs |
|---|---|
| `SimpleService` and `StagingService` interfaces | [CONVENTIONS.md §4, §9](../core/CONVENTIONS.md) |
| Full action reference for every built-in service | [CONVENTIONS.md §7](../core/CONVENTIONS.md) |
| Step-by-step guide for adding a new entity | [API_PATTERN_TEMPLATE.md](../examples/API_PATTERN_TEMPLATE.md) |
| Live example of all three endpoint types | `lib/api/routes/users.py` |
| Live example of `SimpleService` | `lib/services/role_service.py` |
| Live example of `StagingService` | `lib/services/user_service.py` |
| Live example of custom `execute()` | `lib/services/navigation_service.py` |
| EventBus subscribe/publish mechanics | [ARCHITECTURE.md — EventBus section](../core/ARCHITECTURE.md) |
| Import boundary rules | [CONVENTIONS.md §6](../core/CONVENTIONS.md) |
| Test patterns for each service type | [TESTING.md](TESTING.md) |
