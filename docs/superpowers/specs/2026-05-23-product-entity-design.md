# Product Entity — Design Spec

**Date:** 2026-05-23

## Goal

Replace the hardcoded `SAMPLE_PRODUCTS` / `CATALOG` dicts in the Flet views with a real
database-backed Product entity — proving the full framework LEGO pattern (model → repo →
service → route → view) works end-to-end with real data.

## Scope

- Minimal model: `name`, `price`, `stock_qty`, `is_active`
- Immediate CRUD only (no staged ops — User already demonstrates those)
- Public reads, protected writes — extends `router_registry` to support mixed-auth routes
- Flet views stay thin; all logic lives in service + routes
- Views are replaceable; routes are the permanent interface

## Data Layer

### `lib/models/product.py`

```python
class Product(Base):
    __tablename__ = "products"
    id:        Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name:      Mapped[str]       = mapped_column(String, unique=True, index=True)
    price:     Mapped[Decimal]   = mapped_column(Numeric(10, 2))
    stock_qty: Mapped[int]       = mapped_column(Integer, default=0)
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
```

No relationships. Standalone table.

### `lib/repositories/product_repository.py`

`ProductRepository(AbstractRepository[Product])` — override `_serialize` only:
- Stringify `id`
- Cast `price` to `float` (SQLAlchemy returns `Decimal` for `Numeric`)

Base methods (`get`, `create`, `update`, `delete`, `paginate`) are sufficient.

### Migration

New Alembic revision: adds `products` table. Downgrade drops it.
`lib/models/__init__.py` and `lib/database/migrations/env.py` get the `Product` import.

## Service Layer

### `lib/services/product_service.py`

`ProductService(SimpleService)` — five immediate methods:

| Method   | data keys                              | Returns                        |
|----------|----------------------------------------|--------------------------------|
| `create` | `name`, `price`, `stock_qty?`, `is_active?` | product dict              |
| `get`    | `id`                                   | product dict; raises if missing |
| `list`   | `page?`, `page_size?`                  | `PaginatedResult`-compatible dict |
| `update` | `id` + any subset of fields            | updated product dict           |
| `delete` | `id`                                   | `{"deleted": True}`            |

`update` is partial — only keys present in `data` are written. Raises `ValueError` if id not found.
`list` uses `repo.paginate()` and a `_PRODUCT_LIST_FIELDS = frozenset({"id", "name", "price", "stock_qty", "is_active"})` allowlist (same pattern as UserService).

## API Routes

### Router Registry Extension

`router_registry.py` is extended to support a `public_router` attribute alongside the existing
`router`. This is the reusable pattern for any future mixed-auth route file:

```python
# Per discovered module in mount_routes():
if hasattr(sub, "public_router"):
    public.include_router(sub.public_router)
if hasattr(sub, "router"):
    target = public if getattr(sub, "_PUBLIC_ROUTER", False) else protected
    target.include_router(sub.router)
```

Three patterns any route file can now use:

| File exports               | Result                          |
|----------------------------|---------------------------------|
| `router` only              | All routes protected (default)  |
| `router` + `_PUBLIC_ROUTER = True` | All routes public         |
| `public_router` + `router` | Mixed — reads public, writes protected |

### `lib/api/routes/products.py`

Reference implementation of the mixed-auth pattern:

```
public_router  prefix="/products"
  GET  /v1/products          → list (paginated, PaginatedResult)
  GET  /v1/products/{id}     → get by UUID, 404 if missing

router  prefix="/products"
  POST   /v1/products        → create (Bearer JWT required)
  PATCH  /v1/products/{id}   → partial update (Bearer JWT required)
  DELETE /v1/products/{id}   → delete, 404 if missing (Bearer JWT required)
```

Error mapping: `ValueError` from service → 404. Validation errors → 400.

## Flet Views

Both existing views replace hardcoded dicts with real service calls.

### `lib/views/products.py`

`SAMPLE_PRODUCTS` removed. `build_content` calls:
```python
service = self.props["product_service"]
result  = service.execute(ActionRequest(action="list", data={}))
items   = result.data.get("items", [])
```
Renders a `Card` per product with name, price, and a NavButton to `/products/{id}`.

### `lib/views/product_detail.py`

`CATALOG` dict removed. `Params.id` changes from `int` to `str` (UUID string from URL).
`build_content` calls:
```python
result = service.execute(ActionRequest(action="get", data={"id": self.params.id}))
```
If `result.success` is False → render "Product not found" text.
Two-tab layout (overview/stock) preserved.

## Wiring

**`main.py`** additions:
```python
from lib.services.product_service import ProductService

product_service = ProductService(ConnectionRegistry.get())

# in props_factory:
"product_service": product_service,
```

## Tests

| File | Covers |
|---|---|
| `tests/test_product_repo.py` | create, get, paginate, update, delete — in-memory SQLite |
| `tests/test_product_service.py` | create, list paginated, update partial, get-missing raises |
| `tests/test_product_api.py` | GET list 200 (no auth), GET 404, POST 401 without token, POST 201 with token, PATCH, DELETE |
| `tests/test_smoke.py` | add `lib.models.product`, `lib.repositories.product_repository`, `lib.services.product_service` |

## Files Created / Modified

| File | Action |
|---|---|
| `lib/models/product.py` | Create |
| `lib/models/__init__.py` | Modify — add Product import |
| `lib/repositories/product_repository.py` | Create |
| `lib/services/product_service.py` | Create |
| `lib/api/routes/products.py` | Create |
| `lib/api/router_registry.py` | Modify — support `public_router` attribute |
| `lib/views/products.py` | Modify — replace hardcoded list |
| `lib/views/product_detail.py` | Modify — replace hardcoded dict, UUID id |
| `lib/database/migrations/env.py` | Modify — add Product import |
| `lib/database/migrations/versions/*.py` | Create — products table migration |
| `main.py` | Modify — wire ProductService |
| `tests/test_product_repo.py` | Create |
| `tests/test_product_service.py` | Create |
| `tests/test_product_api.py` | Create |
| `tests/test_smoke.py` | Modify |
