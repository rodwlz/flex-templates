# Reusable API Pattern Template

## Overview

The Users/Roles API demonstrates a repeatable, layered pattern for adding any new
entity to the system. Every entity follows the same five-layer stack:

```
ORM Model → Repository → Service → Route File → Router Auto-Discovery
```

The contracts (`ActionRequest` / `ActionResult`) are the single shared interface
across all layers. A UI component, a REST client, and a CLI tool all call
`service.execute(ActionRequest(...))` identically. Follow the steps below in order
and you will have a working, tested entity with minimal boilerplate.

---

## To Add a New Entity — Example: Product

### Step 1: Create the ORM Model

Create `lib/models/product.py`. Mirror the User/Role pattern: use `uuid.UUID` as
the primary key, declare columns with `mapped_column`, and add relationships only
when needed.

**Simple entity (no relationships) — mirrors `Role`:**

```python
# lib/models/product.py
import uuid
from sqlalchemy import String, Uuid, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from lib.database.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
```

**Entity with a many-to-many relationship — mirrors `User` ↔ `Role`:**

```python
# lib/models/product.py  (variant with tags)
import uuid
from typing import TYPE_CHECKING, List
from sqlalchemy import Column, ForeignKey, String, Uuid, Numeric, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from lib.database.base import Base

if TYPE_CHECKING:
    from lib.models.tag import Tag

# Association table must be at module level, before the class
product_tags = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", Uuid, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id",     Uuid, ForeignKey("tags.id",     ondelete="CASCADE"), primary_key=True),
)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        back_populates="products",
        secondary="product_tags",
        lazy="joined",
    )
```

After creating the model, register it so SQLAlchemy includes it in `Base.metadata`.
Open `lib/models/__init__.py` and add:

```python
from lib.models.product import Product  # noqa: F401
```

---

### Step 2: Create the Repository

Create `lib/repositories/product_repository.py`. Set `model = Product`. The base
class provides `get`, `list`, `create`, `update`, and `delete` automatically.
Only add methods when you need queries that the base cannot express with simple
keyword filters.

**Minimal repository (no custom queries) — mirrors `RoleRepository`:**

```python
# lib/repositories/product_repository.py
from lib.models.product import Product
from lib.repositories.base import AbstractRepository


class ProductRepository(AbstractRepository[Product]):
    model = Product
```

**Repository with custom query methods — mirrors `UserRepository`:**

```python
# lib/repositories/product_repository.py
from lib.models.product import Product
from lib.models.tag import Tag
from lib.repositories.base import AbstractRepository


class ProductRepository(AbstractRepository[Product]):
    model = Product

    def list_by_tag(self, tag_name: str) -> list[Product]:
        """List all products that carry a specific tag."""
        with self._factory.session() as s:
            return (
                s.query(self.model)
                 .join(Tag, self.model.tags)
                 .filter(Tag.name == tag_name)
                 .all()
            )

    def list_by_status(self, status: str) -> list[Product]:
        """Convenience — identical to list(status=status) but self-documenting."""
        return self.list(status=status)
```

The base `list(**filters)` already handles equality filters on any column:
`repo.list(status="active")` works without custom code.

---

### Step 3: Create the Service

Choose one base class based on whether the entity needs a preview step:

| Scenario | Base class |
|---|---|
| Simple CRUD, no multi-step preview | `SimpleService` |
| Complex create/update with relationships, or anything that benefits from a "review before commit" step | `StagingService` |

**Simple service — mirrors `RoleService`:**

```python
# lib/services/product_service.py
import uuid
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory
from lib.repositories.product_repository import ProductRepository


class ProductService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def create(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product = repo.create(data)
        return {"id": str(product.id), "name": product.name, "price": float(product.price)}

    def get(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product = repo.get(uuid.UUID(data["id"]))
        if product is None:
            raise ValueError(f"Product {data['id']} not found")
        return {"id": str(product.id), "name": product.name, "price": float(product.price)}

    def list(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        products = repo.list()
        return {
            "products": [
                {"id": str(p.id), "name": p.name, "price": float(p.price)}
                for p in products
            ]
        }

    def delete(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        deleted = repo.delete(uuid.UUID(data["id"]))
        if not deleted:
            raise ValueError(f"Product {data['id']} not found")
        return {"deleted": True}
```

**Staging service — mirrors `UserService` for complex operations:**

```python
# lib/services/product_service.py  (variant with staged tag assignment)
import uuid
from lib.core.interfaces import StagingService
from lib.database.session import SessionFactory
from lib.repositories.product_repository import ProductRepository
from lib.repositories.tag_repository import TagRepository


class ProductService(StagingService):
    """
    Immediate: get, list, delete — one shot, instant commit.
    Staged:    create-with-tags — preview before commit.
    """

    def __init__(self, factory: SessionFactory):
        super().__init__(factory)

    # ===== IMMEDIATE OPERATIONS =====

    def get(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product = repo.get(uuid.UUID(data["id"]))
        if product is None:
            raise ValueError(f"Product {data['id']} not found")
        return {
            "id": str(product.id),
            "name": product.name,
            "tags": [t.name for t in product.tags],
        }

    def list(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        return {
            "products": [
                {"id": str(p.id), "name": p.name}
                for p in repo.list()
            ]
        }

    def delete(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        if not repo.delete(uuid.UUID(data["id"])):
            raise ValueError(f"Product {data['id']} not found")
        return {"deleted": True}

    # ===== STAGED OPERATION =====

    def _stage_impl(self, uow, data: dict) -> dict:
        """Stage product creation with tags. Called by StagingService.stage()."""
        repo = uow.repo(ProductRepository)
        tag_repo = uow.repo(TagRepository)

        product = repo.create({
            "name": data["name"],
            "price": data["price"],
            "description": data.get("description"),
        })

        if tag_ids := data.get("tag_ids"):
            for tag_id in tag_ids:
                tag = tag_repo.get(uuid.UUID(tag_id) if isinstance(tag_id, str) else tag_id)
                if tag:
                    product.tags.append(tag)

        return {"product_id": str(product.id), "tag_count": len(product.tags)}
```

**Key rule:** `SimpleService` dispatches any public method by name automatically.
Define a method named `create` and calling `service.execute(ActionRequest(action="create", data={...}))`
routes to it. Exceptions become `ActionResult(success=False, error=...)` automatically —
you never catch them yourself unless you need to add context.

---

### Step 4: Create the Route File

Create `lib/api/routes/products.py`. The file is auto-discovered by `mount_routes()`
as long as it defines a module-level `router` variable.

**Simple entity routes — mirrors `roles.py`:**

```python
# lib/api/routes/products.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def get_service() -> ProductService:
    return ProductService(ConnectionRegistry.get())


@router.post("")
def create_product(data: dict, service: ProductService = Depends(get_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("")
def list_products(service: ProductService = Depends(get_service)):
    result = service.execute(ActionRequest(action="list", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("/{product_id}")
def get_product(product_id: str, service: ProductService = Depends(get_service)):
    result = service.execute(ActionRequest(action="get", data={"id": product_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.delete("/{product_id}")
def delete_product(product_id: str, service: ProductService = Depends(get_service)):
    result = service.execute(ActionRequest(action="delete", data={"id": product_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data
```

**Adding staged endpoints — mirrors `users.py`:**

For `StagingService`, the service instance must be reused across `stage` → `confirm`
because it stores `_pending` (the open unit-of-work) between calls. Cache it by
factory identity:

```python
# Append to lib/api/routes/products.py
_service_cache: dict[int, ProductService] = {}


def get_service() -> ProductService:  # replaces the simple version above
    factory = ConnectionRegistry.get()
    key = id(factory)
    if key not in _service_cache:
        _service_cache[key] = ProductService(factory)
    return _service_cache[key]


@router.post("/with-tags/stage")
def stage_product_with_tags(data: dict, service: ProductService = Depends(get_service)):
    """Stage creation with tags — returns a preview diff, does not commit."""
    result = service.execute(ActionRequest(action="stage", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/with-tags/confirm")
def confirm_product_with_tags(service: ProductService = Depends(get_service)):
    """Commit the staged product."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/with-tags/cancel")
def cancel_product_with_tags(service: ProductService = Depends(get_service)):
    """Roll back the staged product."""
    result = service.execute(ActionRequest(action="cancel", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

**Adding approval-required endpoints — mirrors `users.py` bulk-delete:**

Use `requires_approval=True` on the `ActionRequest` to signal to clients that a
second explicit step is mandatory. The flag does not change service behavior by
itself — the service or a policy layer checks it and decides what to allow.

```python
@router.post("/bulk-archive/request")
def request_bulk_archive(data: dict, service: ProductService = Depends(get_service)):
    """Stage a bulk archive. Client must call /approve to commit."""
    result = service.execute(ActionRequest(action="stage", data=data, requires_approval=True))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/bulk-archive/approve")
def approve_bulk_archive(service: ProductService = Depends(get_service)):
    """Approve and commit the staged bulk archive."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

---

### Step 5: Wire the Service into the App

Nothing. Drop `lib/api/routes/products.py` with a `router = APIRouter(...)` and
`mount_routes()` in `lib/api/router_registry.py` picks it up automatically:

```python
# lib/api/router_registry.py  — nothing to change
def mount_routes(app: FastAPI, package: str = "lib.api.routes") -> None:
    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if hasattr(sub, "router"):
            app.include_router(sub.router)
```

Verify: start the server and visit `http://localhost:8080/docs` — your new routes
appear automatically under the `products` tag.

---

### Step 6: Write Tests

**Repository tests — mirrors `test_repositories.py`:**

```python
# tests/test_product_repository.py
import uuid
import pytest
from lib.repositories.product_repository import ProductRepository


def test_create_product(db_factory):
    repo = ProductRepository(db_factory)
    product = repo.create({"name": "Widget", "price": 9.99})
    assert product.id is not None
    assert product.name == "Widget"


def test_get_product(db_factory):
    repo = ProductRepository(db_factory)
    product = repo.create({"name": "Gadget", "price": 19.99})
    fetched = repo.get(product.id)
    assert fetched is not None
    assert fetched.name == "Gadget"


def test_get_nonexistent_product(db_factory):
    repo = ProductRepository(db_factory)
    assert repo.get(uuid.uuid4()) is None


def test_list_products(db_factory):
    repo = ProductRepository(db_factory)
    repo.create({"name": "A", "price": 1.00})
    repo.create({"name": "B", "price": 2.00})
    assert len(repo.list()) == 2


def test_update_product(db_factory):
    repo = ProductRepository(db_factory)
    product = repo.create({"name": "Old Name", "price": 5.00})
    updated = repo.update(product.id, {"name": "New Name"})
    assert updated.name == "New Name"


def test_delete_product(db_factory):
    repo = ProductRepository(db_factory)
    product = repo.create({"name": "ToDelete", "price": 1.00})
    assert repo.delete(product.id) is True
    assert repo.get(product.id) is None


def test_delete_nonexistent_product(db_factory):
    repo = ProductRepository(db_factory)
    assert repo.delete(uuid.uuid4()) is False
```

**Service tests — mirrors `test_services.py`:**

```python
# tests/test_product_service.py
from lib.contracts.base import ActionRequest
from lib.services.product_service import ProductService


def test_product_service_create(db_factory):
    service = ProductService(db_factory)
    result = service.execute(ActionRequest(
        action="create",
        data={"name": "Widget", "price": 9.99}
    ))
    assert result.success is True
    assert result.data["name"] == "Widget"


def test_product_service_get(db_factory):
    service = ProductService(db_factory)
    create = service.execute(ActionRequest(action="create", data={"name": "Gadget", "price": 4.99}))
    product_id = create.data["id"]

    result = service.execute(ActionRequest(action="get", data={"id": product_id}))
    assert result.success is True
    assert result.data["name"] == "Gadget"


def test_product_service_get_missing(db_factory):
    import uuid
    service = ProductService(db_factory)
    result = service.execute(ActionRequest(action="get", data={"id": str(uuid.uuid4())}))
    assert result.success is False
    assert "not found" in result.error.lower()


def test_product_service_list(db_factory):
    service = ProductService(db_factory)
    service.execute(ActionRequest(action="create", data={"name": "A", "price": 1.00}))
    service.execute(ActionRequest(action="create", data={"name": "B", "price": 2.00}))

    result = service.execute(ActionRequest(action="list", data={}))
    assert result.success is True
    assert len(result.data["products"]) == 2


def test_product_service_delete(db_factory):
    service = ProductService(db_factory)
    create = service.execute(ActionRequest(action="create", data={"name": "ToDelete", "price": 1.00}))
    product_id = create.data["id"]

    result = service.execute(ActionRequest(action="delete", data={"id": product_id}))
    assert result.success is True


# --- Staged flow (only needed if using StagingService) ---

def test_product_service_stage_confirm(db_factory):
    service = ProductService(db_factory)

    stage = service.execute(ActionRequest(
        action="stage",
        data={"name": "Staged Widget", "price": 15.00, "tag_ids": []}
    ))
    assert stage.success is True
    assert "preview" in stage.data

    confirm = service.execute(ActionRequest(action="confirm", data={}))
    assert confirm.success is True


def test_product_service_stage_cancel(db_factory):
    service = ProductService(db_factory)

    service.execute(ActionRequest(
        action="stage",
        data={"name": "Cancelled Product", "price": 5.00, "tag_ids": []}
    ))

    cancel = service.execute(ActionRequest(action="cancel", data={}))
    assert cancel.success is True

    listed = service.execute(ActionRequest(action="list", data={}))
    assert len(listed.data["products"]) == 0
```

**API integration tests — mirrors `test_api.py`:**

```python
# tests/test_product_api.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import products as products_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base


def _shared_memory_factory() -> SessionFactory:
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def api_client(monkeypatch):
    factory = _shared_memory_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    app = FastAPI()
    app.include_router(products_routes.router)
    return TestClient(app)


def test_create_product_returns_201(api_client):
    response = api_client.post("/products", json={"name": "Widget", "price": 9.99})
    assert response.status_code == 200
    assert response.json()["name"] == "Widget"


def test_list_products_returns_all(api_client):
    api_client.post("/products", json={"name": "A", "price": 1.00})
    api_client.post("/products", json={"name": "B", "price": 2.00})
    response = api_client.get("/products")
    assert response.status_code == 200
    assert len(response.json()["products"]) == 2


def test_get_product_by_id(api_client):
    create = api_client.post("/products", json={"name": "Gadget", "price": 4.99})
    product_id = create.json()["id"]
    response = api_client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["id"] == product_id


def test_get_product_404_when_missing(api_client):
    import uuid
    response = api_client.get(f"/products/{uuid.uuid4()}")
    assert response.status_code == 404


def test_delete_product(api_client):
    create = api_client.post("/products", json={"name": "ToDelete", "price": 1.00})
    product_id = create.json()["id"]
    response = api_client.delete(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
```

The `db_factory` fixture is already defined in `tests/conftest.py` — every test
that takes `db_factory` as a parameter gets a fresh in-memory SQLite database
automatically.

---

## Key Principles

### 1. Contracts First

`ActionRequest` and `ActionResult` are defined in `lib/contracts/base.py` and are
the only interface callers see. Define your action names (`"create"`, `"get"`,
`"list"`, `"delete"`, `"stage"`, `"confirm"`, `"cancel"`) before writing any
service code. The names are the contract — keep them stable.

### 2. Repository Pattern

All database access lives in repository classes, never in services directly. A
service creates a repository instance, calls methods on it, and returns a plain
dict. The repository owns the session context (`with self._factory.session() as s`).

The base class (`AbstractRepository`) handles the session lifecycle automatically —
individual repositories only override what is different.

### 3. Service Layer

Business logic lives in services. Repositories do not validate; services do not
open sessions directly. This split keeps each layer narrow:

```
Route handler  →  ActionRequest
Service        →  validates, orchestrates, returns dict
Repository     →  SQL queries, returns ORM objects
```

### 4. Three Operation Types

| Type | When to use | HTTP shape | Service method |
|---|---|---|---|
| Immediate | Simple CRUD, no side-effect preview | `POST/GET/DELETE /entity` | Named method in `SimpleService` |
| Staged | Multi-step with relationships, or user needs a diff before committing | `POST /entity/stage`, `POST /entity/confirm`, `POST /entity/cancel` | `_stage_impl()` in `StagingService` |
| Approval | High-risk or irreversible operations requiring an explicit second confirmation | `POST /entity/action/request`, `POST /entity/action/approve` | `_stage_impl()` with `requires_approval=True` |

Use `SimpleService` unless you need staging. Adding `StagingService` to an entity
that does not need it creates unnecessary complexity.

### 5. Dependency Injection

Services depend only on `SessionFactory` (from `ConnectionRegistry`). Route files
call `ConnectionRegistry.get()` in the FastAPI dependency function. This means:

- Tests swap in an in-memory factory with `monkeypatch.setattr` — no mocking needed.
- Multiple databases are supported by passing a name to `ConnectionRegistry.get("analytics")`.
- Services never import from routes — the dependency flows one way only.

### 6. Auto-Discovery

Any file placed in `lib/api/routes/` that defines `router = APIRouter(...)` is
mounted automatically. There is no registration step, no list to update.

---

## Testing Checklist

Before considering an entity complete, verify each of the following:

- [ ] Repository: `create`, `get`, `list`, `update`, `delete` all have unit tests
- [ ] Repository: custom query methods each have at least one positive and one
      negative test (e.g., `list_by_role` with zero matching rows)
- [ ] Service: every action name tested via `service.execute(ActionRequest(...))`
- [ ] Service: missing-entity paths return `result.success == False` (not exceptions)
- [ ] Service (staged): `stage → confirm` flow tested end-to-end
- [ ] Service (staged): `stage → cancel` verifies the record was NOT committed
- [ ] API: happy-path GET and POST return correct status codes and body shape
- [ ] API: 404 returned for a valid-format UUID that does not exist in the database
- [ ] Coverage: run `pytest --cov=lib --cov-fail-under=85` and confirm it passes

The `db_factory` fixture in `tests/conftest.py` is available in every test file
without any extra imports. Use it. Do not create real databases in tests.
