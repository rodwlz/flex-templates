---
title: "Adding a New Entity to the Backend Adapter"
category: guide
audience: [developer]
related:
  - ../core/CONVENTIONS.md
  - ../reference/MIGRATIONS.md
  - ADDING_STUFF.md
agent_priority: high
---

# Adding a New Entity End-to-End

The standard recipe when you add a new domain object (Order, Product, Report, etc.)
that Flet admin views need to create, list, update, or delete.

**Full path:** model → migration → repository → service → adapter → view

---

## 1. Write the model (`lib/models/`)

```python
# lib/models/order.py
import uuid
from sqlalchemy import String, Numeric, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from lib.database.base import Base

class Order(Base):
    __tablename__ = "orders"
    id:       Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id:  Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    total:    Mapped[float]     = mapped_column(Numeric(10, 2), nullable=False)
    status:   Mapped[str]       = mapped_column(String(20), default="pending")
```

Register it in `lib/models/__init__.py`:

```python
from lib.models import user, role, order  # noqa: F401
```

And in `lib/database/migrations/env.py`:

```python
import lib.models.user    # noqa: F401
import lib.models.role    # noqa: F401
import lib.models.order   # noqa: F401  ← add
```

---

## 2. Generate and apply the migration

```bash
alembic revision --autogenerate -m "add orders table"
alembic upgrade head
```

Review the generated file in `lib/database/migrations/versions/` before applying.

---

## 3. Write the repository (`lib/repositories/`)

Start minimal — add query methods only when a view actually needs them.

```python
# lib/repositories/order_repository.py
from lib.repositories.base import AbstractRepository
from lib.models.order import Order

class OrderRepository(AbstractRepository[Order]):
    model = Order
    # No overrides needed for scalar-only entities.
    # Override _serialize() to add relationship fields:
    # def _serialize(self, obj) -> dict:
    #     d = super()._serialize(obj)
    #     d["items"] = [i.name for i in obj.items]
    #     return d
```

> **When to override `_serialize()`?** The base implementation serializes scalar
> columns only. Override `_serialize()` to add relationship fields (e.g. `order.items`,
> `user.roles`). The hook is called inside the open session, so lazy-loaded attributes
> are accessible. Returning ORM objects causes `DetachedInstanceError` after the
> session closes, but dicts returned from `_serialize()` are safe to use anywhere.

---

## 4. Write the service (`lib/services/`)

```python
# lib/services/order_service.py
from lib.core.interfaces import SimpleService
from lib.repositories.order_repository import OrderRepository

class OrderService(SimpleService):
    def __init__(self, factory):
        self._repo = OrderRepository(factory)

    def list(self, data: dict) -> dict:
        page      = data.get("page", 1)
        page_size = data.get("page_size", 20)
        return self._repo.paginate(page=page, page_size=page_size)

    def create(self, data: dict) -> dict:
        order = self._repo.create(data)
        return {"id": str(order.id), "status": order.status}

    def delete(self, data: dict) -> dict:
        deleted = self._repo.delete(data["id"])
        return {"deleted": deleted}
```

`SimpleService` auto-dispatches `action="list"` → `self.list(data)` etc. No `execute()` override needed.

---

## 5. Add methods to `ServiceBackendAdapter` (`lib/adapters/backend_adapter.py`)

This is the only place admin views touch services. Add one method per view action.

```python
# In ServiceBackendAdapter:

def list_orders(self, page: int = 1, page_size: int = 20) -> dict:
    result = self._order_service.execute(
        ActionRequest(action="list", data={"page": page, "page_size": page_size})
    )
    if not result.success:
        raise RuntimeError(result.error)
    return result.data

def create_order(self, data: dict) -> dict:
    result = self._order_service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise RuntimeError(result.error)
    return result.data

def delete_order(self, order_id: str) -> None:
    self._order_service.execute(ActionRequest(action="delete", data={"id": order_id}))
```

And wire `OrderService` into `ServiceBackendAdapter.__init__`:

```python
def __init__(self, factory, user_service, scheduler, order_service=None):
    ...
    self._order_service = order_service or OrderService(factory)
```

---

## 6. Wire in `main.py`

```python
from lib.services.order_service import OrderService

def _make_backend(factory):
    return ServiceBackendAdapter(
        factory=factory,
        user_service=UserService(factory),
        order_service=OrderService(factory),   # ← add
        scheduler=scheduler,
    )
```

That's it. The `backend` prop already flows to every view — no other `main.py` changes needed.

---

## 7. Use in a view

```python
class OrdersView(ProtectedView):
    title = "Orders"

    def build_content(self):
        result = self._backend.list_orders(page=1, page_size=20)
        # result = {"items": [...], "total": N, "page": 1, "pages": M}
        ...
```

---

## Quick Reference: What lives where

| Thing | File | Notes |
|---|---|---|
| ORM table definition | `lib/models/<entity>.py` | Inherit `Base` |
| Model registration | `lib/models/__init__.py` + `migrations/env.py` | Both required |
| Migration | `lib/database/migrations/versions/` | Auto-generated, review before applying |
| DB CRUD | `lib/repositories/<entity>_repository.py` | Return dicts, not ORM objects |
| Business logic | `lib/services/<entity>_service.py` | `SimpleService` subclass |
| View-facing API | `lib/adapters/backend_adapter.py` | One method per action |
| Wiring | `main.py` | Pass service to `_make_backend()` |
| Flet view | `lib/views/<path>/<entity>.py` | Call `self._backend.<method>()` |

---

## Common mistakes

**Returning ORM objects from repository methods**
Session closes when the `with factory.session()` block exits. Accessing `.roles` or
any lazy-loaded attribute after that raises `DetachedInstanceError`. Always return
plain dicts materialized inside the `with` block.

**Calling `self._service.method()` directly from a view**
Views must not import services. Pull everything through `self._backend` (the adapter).
If a method is missing from the adapter, add it there.

**Forgetting to register the model in `env.py`**
`alembic revision --autogenerate` will not see the new table if the model module
isn't imported in `lib/database/migrations/env.py`. The migration will be empty.

**Running alembic from the wrong directory**
Always run from the project root where `alembic.ini` lives.
