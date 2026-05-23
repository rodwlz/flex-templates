# Product Entity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded `SAMPLE_PRODUCTS`/`CATALOG` dicts with a real database-backed Product entity — proving the full framework LEGO stack (model → repo → service → route → view) end-to-end.

**Architecture:** `ProductService(SimpleService)` with immediate CRUD. Public GETs / protected writes split via a `public_router` + `router` convention that extends `router_registry.py` once and is reusable for all future mixed-auth route files. Flet views stay thin — they call the service, render the result.

**Tech Stack:** SQLAlchemy 2.0 mapped_column, Alembic autogenerate migration, FastAPI APIRouter, Flet BaseView, pytest + httpx TestClient.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `lib/models/product.py` | Create | Product ORM model |
| `lib/models/__init__.py` | Modify | Register Product on Base.metadata |
| `lib/database/migrations/env.py` | Modify | Register Product for autogenerate |
| `lib/database/migrations/versions/*.py` | Create (generated) | `products` table migration |
| `lib/repositories/product_repository.py` | Create | CRUD + `_serialize` override |
| `lib/services/product_service.py` | Create | `SimpleService` CRUD with pagination |
| `lib/api/router_registry.py` | Modify | Support `public_router` attribute |
| `lib/api/routes/products.py` | Create | Public GETs + protected writes |
| `lib/views/products.py` | Modify | Replace `SAMPLE_PRODUCTS` with service |
| `lib/views/product_detail.py` | Modify | Replace `CATALOG` with service; UUID id |
| `main.py` | Modify | Wire `ProductService` into `_ctx` + props |
| `tests/test_product_repo.py` | Create | Repo CRUD tests |
| `tests/test_product_service.py` | Create | Service unit tests |
| `tests/test_product_api.py` | Create | Route integration tests |
| `tests/test_smoke.py` | Modify | Add new module imports; wire product_service into configured_router fixture |

---

## Task 1: Product Model

**Files:**
- Create: `lib/models/product.py`
- Modify: `lib/models/__init__.py`
- Test: (import-only — smoke test catches this)

- [ ] **Step 1: Write a failing import test**

Add to `tests/test_product_repo.py` (create the file):

```python
from lib.models.product import Product


def test_product_model_has_expected_columns():
    cols = {c.key for c in Product.__table__.columns}
    assert cols == {"id", "name", "price", "stock_qty", "is_active"}
```

- [ ] **Step 2: Run it to see it fail**

```
pytest tests/test_product_repo.py::test_product_model_has_expected_columns -v
```
Expected: `ModuleNotFoundError: No module named 'lib.models.product'`

- [ ] **Step 3: Create `lib/models/product.py`**

```python
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from lib.database.base import Base


class Product(Base):
    __tablename__ = "products"

    id:        Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name:      Mapped[str]       = mapped_column(String, unique=True, index=True)
    price:     Mapped[Decimal]   = mapped_column(Numeric(10, 2))
    stock_qty: Mapped[int]       = mapped_column(Integer, default=0)
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
```

- [ ] **Step 4: Register Product in `lib/models/__init__.py`**

Add one line after the existing imports:

```python
from lib.models.product import Product  # noqa: F401
```

Result:
```python
from lib.models.user import User  # noqa: F401
from lib.models.role import Role  # noqa: F401
from lib.models.password_reset_token import PasswordResetToken  # noqa: F401
from lib.models.product import Product  # noqa: F401
```

- [ ] **Step 5: Run the test**

```
pytest tests/test_product_repo.py::test_product_model_has_expected_columns -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```
git add lib/models/product.py lib/models/__init__.py tests/test_product_repo.py
git commit -m "feat: add Product ORM model"
```

---

## Task 2: ProductRepository

**Files:**
- Create: `lib/repositories/product_repository.py`
- Modify: `tests/test_product_repo.py`

- [ ] **Step 1: Write failing repo tests**

Add to `tests/test_product_repo.py`:

```python
import uuid
import pytest

from lib.repositories.product_repository import ProductRepository


@pytest.fixture
def product_repo(db_factory):
    return ProductRepository(db_factory)


def test_create_product(product_repo):
    p = product_repo.create({"name": "Widget", "price": "9.99", "stock_qty": 10})
    assert p.id is not None
    assert p.name == "Widget"


def test_get_product(product_repo):
    p = product_repo.create({"name": "Gadget", "price": "19.99"})
    fetched = product_repo.get(p.id)
    assert fetched is not None
    assert fetched.name == "Gadget"


def test_get_missing_product(product_repo):
    assert product_repo.get(uuid.uuid4()) is None


def test_update_product(product_repo):
    p = product_repo.create({"name": "Gizmo", "price": "5.00", "stock_qty": 3})
    updated = product_repo.update(p.id, {"stock_qty": 99})
    assert updated.stock_qty == 99


def test_delete_product(product_repo):
    p = product_repo.create({"name": "Doohickey", "price": "1.00"})
    assert product_repo.delete(p.id) is True
    assert product_repo.get(p.id) is None


def test_paginate_products(product_repo):
    for i in range(3):
        product_repo.create({"name": f"Item-{i}", "price": f"{i + 1}.00"})
    result = product_repo.paginate(page=1, page_size=2)
    assert result["total"] == 3
    assert result["pages"] == 2
    assert len(result["items"]) == 2
    assert isinstance(result["items"][0]["id"], str)   # _serialize stringifies UUID
    assert isinstance(result["items"][0]["price"], float)  # _serialize casts Decimal
```

- [ ] **Step 2: Run to see failures**

```
pytest tests/test_product_repo.py -v -k "not test_product_model"
```
Expected: `ImportError: cannot import name 'ProductRepository'`

- [ ] **Step 3: Create `lib/repositories/product_repository.py`**

```python
from lib.models.product import Product
from lib.repositories.base import AbstractRepository


class ProductRepository(AbstractRepository[Product]):
    model = Product

    def _serialize(self, obj) -> dict:
        d = super()._serialize(obj)
        d["id"] = str(d["id"])
        d["price"] = float(d["price"])
        return d
```

- [ ] **Step 4: Run the tests**

```
pytest tests/test_product_repo.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```
git add lib/repositories/product_repository.py tests/test_product_repo.py
git commit -m "feat: add ProductRepository with _serialize override"
```

---

## Task 3: ProductService

**Files:**
- Create: `lib/services/product_service.py`
- Create: `tests/test_product_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_product_service.py`:

```python
import pytest
from lib.services.product_service import ProductService
from lib.contracts.base import ActionRequest


@pytest.fixture
def product_service(db_factory):
    return ProductService(db_factory)


def test_create_product(product_service):
    result = product_service.execute(ActionRequest(
        action="create",
        data={"name": "Sprocket", "price": 4.99, "stock_qty": 20},
    ))
    assert result.success
    assert result.data["name"] == "Sprocket"
    assert result.data["is_active"] is True


def test_get_product(product_service):
    created = product_service.execute(ActionRequest(
        action="create", data={"name": "Cog", "price": 2.50},
    ))
    result = product_service.execute(ActionRequest(
        action="get", data={"id": created.data["id"]},
    ))
    assert result.success
    assert result.data["name"] == "Cog"


def test_get_missing_product_returns_failure(product_service):
    import uuid
    result = product_service.execute(ActionRequest(
        action="get", data={"id": str(uuid.uuid4())},
    ))
    assert not result.success
    assert "not found" in result.error.lower()


def test_list_products_paginated(product_service):
    for i in range(5):
        product_service.execute(ActionRequest(
            action="create", data={"name": f"Part-{i}", "price": float(i + 1)},
        ))
    result = product_service.execute(ActionRequest(
        action="list", data={"page": 1, "page_size": 3},
    ))
    assert result.success
    assert result.data["total"] == 5
    assert len(result.data["items"]) == 3
    assert result.data["pages"] == 2


def test_list_items_contain_no_sensitive_fields(product_service):
    product_service.execute(ActionRequest(
        action="create", data={"name": "Safe", "price": 1.0},
    ))
    result = product_service.execute(ActionRequest(action="list", data={}))
    item = result.data["items"][0]
    assert set(item.keys()) == {"id", "name", "price", "stock_qty", "is_active"}


def test_update_product(product_service):
    created = product_service.execute(ActionRequest(
        action="create", data={"name": "Bolt", "price": 0.50, "stock_qty": 100},
    ))
    result = product_service.execute(ActionRequest(
        action="update",
        data={"id": created.data["id"], "stock_qty": 50},
    ))
    assert result.success
    assert result.data["stock_qty"] == 50
    assert result.data["name"] == "Bolt"  # unchanged


def test_delete_product(product_service):
    created = product_service.execute(ActionRequest(
        action="create", data={"name": "Nut", "price": 0.25},
    ))
    del_result = product_service.execute(ActionRequest(
        action="delete", data={"id": created.data["id"]},
    ))
    assert del_result.success
    get_result = product_service.execute(ActionRequest(
        action="get", data={"id": created.data["id"]},
    ))
    assert not get_result.success
```

- [ ] **Step 2: Run to see failures**

```
pytest tests/test_product_service.py -v
```
Expected: `ImportError: cannot import name 'ProductService'`

- [ ] **Step 3: Create `lib/services/product_service.py`**

```python
import uuid

from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory
from lib.repositories.product_repository import ProductRepository


_PRODUCT_LIST_FIELDS = frozenset({"id", "name", "price", "stock_qty", "is_active"})


class ProductService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def create(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product = repo.create(data)
        return {
            "id": str(product.id),
            "name": product.name,
            "price": float(product.price),
            "stock_qty": product.stock_qty,
            "is_active": product.is_active,
        }

    def get(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product = repo.get(uuid.UUID(data["id"]))
        if product is None:
            raise ValueError(f"Product {data['id']} not found")
        return {
            "id": str(product.id),
            "name": product.name,
            "price": float(product.price),
            "stock_qty": product.stock_qty,
            "is_active": product.is_active,
        }

    def list(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        page = data.get("page", 1)
        page_size = data.get("page_size", 20)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [
            {k: v for k, v in item.items() if k in _PRODUCT_LIST_FIELDS}
            for item in result["items"]
        ]
        return result

    def update(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product_id = uuid.UUID(data["id"])
        update_data = {k: v for k, v in data.items() if k != "id"}
        product = repo.update(product_id, update_data)
        if product is None:
            raise ValueError(f"Product {data['id']} not found")
        return {
            "id": str(product.id),
            "name": product.name,
            "price": float(product.price),
            "stock_qty": product.stock_qty,
            "is_active": product.is_active,
        }

    def delete(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        deleted = repo.delete(uuid.UUID(data["id"]))
        if not deleted:
            raise ValueError(f"Product {data['id']} not found")
        return {"deleted": True}
```

- [ ] **Step 4: Run the tests**

```
pytest tests/test_product_service.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```
git add lib/services/product_service.py tests/test_product_service.py
git commit -m "feat: add ProductService with immediate CRUD"
```

---

## Task 4: Extend Router Registry for Mixed-Auth Routes

**Files:**
- Modify: `lib/api/router_registry.py`
- Create: `tests/test_product_api.py` (partial — registry test only)

- [ ] **Step 1: Write a failing test for `public_router` mounting**

Create `tests/test_product_api.py`:

```python
"""
Integration tests for GET /v1/products (public) and write endpoints (protected).
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, APIRouter

from lib.api.router_registry import mount_routes
from lib.config.settings import AppConfig


def test_public_router_attribute_is_mounted_without_auth(monkeypatch):
    """A module with public_router + router should have GETs accessible without a token."""
    from lib.api.routes import products as products_routes
    from tests.conftest import _v1_app

    # Build a test app using only the products public_router (no auth)
    app = _v1_app(products_routes.public_router)
    client = TestClient(app)
    resp = client.get("/v1/products")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to see it fail**

```
pytest tests/test_product_api.py::test_public_router_attribute_is_mounted_without_auth -v
```
Expected: `ImportError` or `AttributeError: module has no attribute 'public_router'`

- [ ] **Step 3: Modify `lib/api/router_registry.py`**

Replace the inner `if/else` block inside `mount_routes`. The full function after the change:

```python
def mount_routes(app: FastAPI, config, package: str = "lib.api.routes") -> None:
    from lib.api.v1 import make_v1_router
    v1_router, public, protected = make_v1_router(config)

    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if not hasattr(sub, "router") and not hasattr(sub, "public_router"):
            continue
        if hasattr(sub, "public_router"):
            public.include_router(sub.public_router)
        if hasattr(sub, "router"):
            target = public if getattr(sub, "_PUBLIC_ROUTER", False) else protected
            target.include_router(sub.router)

    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
```

- [ ] **Step 4: Create `lib/api/routes/products.py`** (minimal — just enough for the test)

```python
from fastapi import APIRouter, Depends, HTTPException, Query

from lib.contracts.base import ActionRequest, PaginatedResult
from lib.database.session import ConnectionRegistry
from lib.services.product_service import ProductService

public_router = APIRouter(prefix="/products", tags=["products"])
router = APIRouter(prefix="/products", tags=["products"])


def _get_service() -> ProductService:
    return ProductService(ConnectionRegistry.get())


@public_router.get("", response_model=PaginatedResult)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    service: ProductService = Depends(_get_service),
):
    result = service.execute(ActionRequest(
        action="list", data={"page": page, "page_size": page_size},
    ))
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@public_router.get("/{product_id}")
def get_product(product_id: str, service: ProductService = Depends(_get_service)):
    result = service.execute(ActionRequest(action="get", data={"id": product_id}))
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@router.post("", status_code=201)
def create_product(data: dict, service: ProductService = Depends(_get_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@router.patch("/{product_id}")
def update_product(product_id: str, data: dict, service: ProductService = Depends(_get_service)):
    result = service.execute(ActionRequest(
        action="update", data={"id": product_id, **data},
    ))
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data


@router.delete("/{product_id}")
def delete_product(product_id: str, service: ProductService = Depends(_get_service)):
    result = service.execute(ActionRequest(action="delete", data={"id": product_id}))
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return result.data
```

- [ ] **Step 5: Run the test**

```
pytest tests/test_product_api.py::test_public_router_attribute_is_mounted_without_auth -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```
git add lib/api/router_registry.py lib/api/routes/products.py tests/test_product_api.py
git commit -m "feat: extend router_registry for public_router; add products routes"
```

---

## Task 5: Full Product API Tests

**Files:**
- Modify: `tests/test_product_api.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add a `product_client` fixture to `tests/conftest.py`**

Add at the bottom of `tests/conftest.py`:

```python
@pytest.fixture
def product_client(http_factory):
    from lib.api.routes import products as products_routes
    from lib.services.product_service import ProductService
    # products public_router has no auth, router (writes) has auth enforced by the v1 contract.
    # For write-endpoint tests we use _v1_app with just the write router and inject a token manually.
    public_app = _v1_app(products_routes.public_router)
    write_app  = _v1_app(products_routes.router)
    return (
        TestClient(public_app),   # index 0 — no auth needed
        TestClient(write_app),    # index 1 — no auth (v1 contract stripped in _v1_app)
        ProductService(http_factory),
    )
```

Import `TestClient` at the top of `tests/conftest.py` (it may already be there; add if missing):
```python
from fastapi.testclient import TestClient
```

- [ ] **Step 2: Write the remaining API tests in `tests/test_product_api.py`**

Append to the existing file:

```python
def test_list_products_returns_paginated_result(product_client):
    public_client, _, service = product_client
    service.execute(ActionRequest(action="create", data={"name": "P1", "price": 1.0}))
    service.execute(ActionRequest(action="create", data={"name": "P2", "price": 2.0}))
    resp = public_client.get("/v1/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_get_product_returns_200(product_client):
    public_client, _, service = product_client
    created = service.execute(ActionRequest(
        action="create", data={"name": "Bolt", "price": 0.99},
    ))
    resp = public_client.get(f"/v1/products/{created.data['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Bolt"


def test_get_missing_product_returns_404(product_client):
    public_client, _, _ = product_client
    resp = public_client.get(f"/v1/products/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_create_product_returns_201(product_client):
    _, write_client, _ = product_client
    resp = write_client.post("/v1/products", json={"name": "Sprocket", "price": 4.99})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Sprocket"


def test_update_product(product_client):
    _, write_client, service = product_client
    created = service.execute(ActionRequest(
        action="create", data={"name": "Cog", "price": 2.0, "stock_qty": 10},
    ))
    resp = write_client.patch(
        f"/v1/products/{created.data['id']}", json={"stock_qty": 99},
    )
    assert resp.status_code == 200
    assert resp.json()["stock_qty"] == 99


def test_delete_product(product_client):
    _, write_client, service = product_client
    created = service.execute(ActionRequest(
        action="create", data={"name": "Nut", "price": 0.25},
    ))
    resp = write_client.delete(f"/v1/products/{created.data['id']}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
```

- [ ] **Step 3: Run all product API tests**

```
pytest tests/test_product_api.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 4: Commit**

```
git add tests/test_product_api.py tests/conftest.py
git commit -m "test: full product API integration tests"
```

---

## Task 6: Alembic Migration

**Files:**
- Modify: `lib/database/migrations/env.py`
- Create: `lib/database/migrations/versions/<revision>_add_products_table.py` (generated)

- [ ] **Step 1: Register Product in `lib/database/migrations/env.py`**

Add one line after the existing model imports:

```python
import lib.models.product  # noqa: F401 — registers Product on Base.metadata
```

Result (the three import lines together):
```python
import lib.models.user  # noqa: F401 — registers User on Base.metadata
import lib.models.role  # noqa: F401 — registers Role on Base.metadata
import lib.models.password_reset_token  # noqa: F401 — registers PasswordResetToken
import lib.models.product  # noqa: F401 — registers Product on Base.metadata
```

- [ ] **Step 2: Generate the migration**

```
alembic revision --autogenerate -m "add products table"
```

Alembic creates a new file in `lib/database/migrations/versions/`. Open it and verify the `upgrade()` function contains:
- `op.create_table('products', ...)` with columns: `id`, `name`, `price`, `stock_qty`, `is_active`
- `op.create_index(...)` on `products.name` (autogenerated from `index=True`)
- `downgrade()` drops the index then the table

If autogenerate produced anything extra (e.g. alembic detecting the `users` table as changed), remove those blocks — only the `products` table should appear.

- [ ] **Step 3: Apply the migration**

```
alembic upgrade head
```

Expected output ends with: `Running upgrade <prev_revision> -> <new_revision>, add products table`

- [ ] **Step 4: Verify**

```
alembic current
```

Expected: `<new_revision> (head)`

- [ ] **Step 5: Commit**

```
git add lib/database/migrations/env.py lib/database/migrations/versions/
git commit -m "feat: alembic migration — add products table"
```

---

## Task 7: Flet Views

**Files:**
- Modify: `lib/views/products.py`
- Modify: `lib/views/product_detail.py`

- [ ] **Step 1: Rewrite `lib/views/products.py`**

Full file replacement (removes `SAMPLE_PRODUCTS`):

```python
import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.nav_button import NavButton


class ProductsView(BaseView):
    title = "Products"

    def build_content(self):
        service = self.props.get("product_service")
        if service is None:
            return ft.Text("product_service not configured", color=ft.Colors.RED_400)

        result = service.execute(ActionRequest(action="list", data={}))
        items = result.data.get("items", []) if result.success else []

        cards = [
            Card(
                title=p["name"],
                body=ft.Column(
                    [
                        ft.Text(f"${p['price']:.2f}"),
                        NavButton(
                            "View Details", f"/products/{p['id']}", self.nav_service
                        ),
                    ],
                    spacing=10,
                ),
            )
            for p in items
        ]

        return ft.Column(
            [
                ft.Text("Products", size=28, weight=ft.FontWeight.BOLD),
                *(cards if cards else [ft.Text("No products found.")]),
            ],
            spacing=15,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return ProductsView(page, props).render()
```

- [ ] **Step 2: Rewrite `lib/views/product_detail.py`**

Full file replacement (removes `CATALOG`, changes `id: int` → `id: str`):

```python
import flet as ft
from pydantic import BaseModel

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.back_button import BackButton


class ProductDetailView(BaseView):
    title = "Product"

    class Params(BaseModel):
        id: str                # UUID string from URL path: /products/{id}
        tab: str = "overview"  # from query string: ?tab=stock

    def build_content(self):
        service = self.props.get("product_service")
        if service is None:
            return ft.Text("product_service not configured", color=ft.Colors.RED_400)

        result = service.execute(ActionRequest(action="get", data={"id": self.params.id}))
        if not result.success:
            return ft.Text("Product not found", color=ft.Colors.RED_400)

        product = result.data
        body = self._tab_body(self.params.tab, product)

        return ft.Column(
            [
                ft.Text(product["name"], size=28, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        self._tab_link("overview", self.params.id),
                        self._tab_link("stock", self.params.id),
                    ],
                    spacing=15,
                ),
                Card(title=self.params.tab.capitalize(), body=body),
                BackButton(self.nav_service),
            ],
            spacing=15,
        )

    def _tab_body(self, tab: str, product: dict):
        if tab == "stock":
            return ft.Text(f"In stock: {product['stock_qty']} units")
        return ft.Text(f"Price: ${product['price']:.2f}")

    def _tab_link(self, tab: str, product_id: str):
        return ft.TextButton(
            tab.capitalize(),
            on_click=lambda _: self.nav_service.execute(
                ActionRequest(
                    action="visit",
                    data={"url": f"/products/{product_id}?tab={tab}"},
                )
            ),
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return ProductDetailView(page, props).render()
```

- [ ] **Step 3: Run existing smoke tests to confirm views still render**

```
pytest tests/test_smoke.py -v
```

Expected: all smoke tests PASS. The views render gracefully even without a `product_service` in props (they show "not configured" text rather than crashing).

- [ ] **Step 4: Commit**

```
git add lib/views/products.py lib/views/product_detail.py
git commit -m "feat: wire products and product_detail views to ProductService"
```

---

## Task 8: Wire `ProductService` into `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add the import at the top of `main.py`**

Add after the `UserService` import line:

```python
from lib.services.product_service import ProductService
```

- [ ] **Step 2: Initialise `product_service` in `_ctx` before the try block**

Find the line `_ctx: dict = {}` and add:
```python
_ctx: dict = {}
_ctx["product_service"] = None   # set in each DB branch below
```

- [ ] **Step 3: Create `ProductService` in both DB branches**

Find the block that sets `_ctx["backend"]`. It appears twice — once for the primary DB path and once for the SQLite fallback. Add `_ctx["product_service"] = ProductService(factory)` in both:

**Primary DB branch** (inside the `try:` block after `_ctx["backend"] = _make_backend(_primary_factory)`):
```python
_ctx["backend"] = _make_backend(_primary_factory)
_ctx["product_service"] = ProductService(_primary_factory)
```

**SQLite fallback branch** (after `_ctx["backend"] = _make_backend(_sqlite_factory)`):
```python
_ctx["backend"] = _make_backend(_sqlite_factory)
_ctx["product_service"] = ProductService(_sqlite_factory)
```

**Error branch** — also initialise to None so the key always exists:
```python
_startup_error = str(exc)
_ctx["backend"] = None
_ctx["product_service"] = None
```

- [ ] **Step 3: Add `product_service` to `props_factory`**

Inside `router.set_props_factory(lambda: { ... })`, add:

```python
"product_service": _ctx.get("product_service"),
```

Place it under the `"user_repo"` line in the `# Data access` section.

- [ ] **Step 4: Also re-wire on vault unlock**

Inside `_on_vault_unlocked`, find where `_ctx["backend"]` is updated after the primary DB becomes available. Add the same line for `product_service`:

```python
_ctx["backend"] = _make_backend(factory)
_ctx["product_service"] = ProductService(factory)
```

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -q
```
Expected: all existing tests pass (575+) with no regressions.

- [ ] **Step 6: Commit**

```
git add main.py
git commit -m "feat: wire ProductService into main.py props_factory"
```

---

## Task 9: Smoke Test Updates

**Files:**
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Add new module imports to the parametrize list**

In `tests/test_smoke.py`, find the `@pytest.mark.parametrize("module_path", [...])` list and add:

```python
"lib.models.product",
"lib.repositories.product_repository",
"lib.services.product_service",
"lib.api.routes.products",
```

- [ ] **Step 2: Update `configured_router` fixture to inject `product_service`**

Replace the existing `configured_router` fixture (add `nav_service` and `db_factory` as parameters so pytest injects them):

```python
@pytest.fixture
def configured_router(router, nav_service, db_factory):
    from lib.services.product_service import ProductService
    router.register("/products/{id}", "lib.views.product_detail")
    router.set_props_factory(lambda: {
        "nav_service": nav_service,
        "product_service": ProductService(db_factory),
    })
    return router
```

- [ ] **Step 3: Run the full smoke test**

```
pytest tests/test_smoke.py -v
```
Expected: all smoke tests PASS, including `/products` and `/products/1` (renders "Product not found" gracefully for the non-existent UUID `"1"`).

- [ ] **Step 4: Run the full suite one final time**

```
pytest tests/ -q
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```
git add tests/test_smoke.py
git commit -m "test: add product module smoke tests; inject product_service into configured_router"
```
