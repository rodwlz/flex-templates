# Auth Gaps — Design Spec

**Date:** 2026-05-22  
**Status:** Approved  
**Scope:** Four independent additions to the existing user/auth layer

---

## What This Builds

Four production-readiness gaps closed in the existing auth layer:

1. **`is_active` flag** — block disabled accounts from logging in; new column on `users`
2. **Registration endpoint** — `POST /v1/auth/register` (public, no Bearer)
3. **Password reset** — token-based, token returned in response body; new `password_reset_tokens` table
4. **Pagination metadata** — `PaginatedResult` contract + `list_paginated` on `AbstractRepository`; `GET /v1/users` adopts it

Each change is independent. They share one Alembic migration (`is_active` column + `password_reset_tokens` table).

---

## Architecture

```
lib/contracts/base.py          ← add PaginatedResult
lib/models/user.py             ← add is_active column
lib/models/password_reset_token.py  ← NEW: PasswordResetToken ORM model
lib/repositories/base.py       ← add list_paginated()
lib/repositories/password_reset_token_repository.py  ← NEW
lib/services/user_service.py   ← add request_reset(), reset_password()
lib/api/routes/auth.py         ← add /register, /forgot-password, /reset-password
lib/api/routes/users.py        ← update GET / to return PaginatedResult
lib/database/migrations/env.py ← import new model for autogenerate
```

One migration covers both schema changes.

---

## 1. `is_active` Flag

### Model change

Add to `lib/models/user.py` alongside existing columns:

```python
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

Default `True` — existing rows stay active after migration.

### Login enforcement

In `lib/api/routes/auth.py`, the login handler calls `user_service.login(username, password)`.  
`UserService.login` (or the equivalent in the auth flow) must check `is_active` **after** password verification and **before** issuing the JWT:

```python
if not user["is_active"]:
    raise HTTPException(status_code=401, detail="Account is disabled")
```

The check belongs in the service method, not the route handler, so it applies to any future auth flow that calls the same method.

### Serialization

`UserRepository._serialize()` must include `is_active` in the returned dict.

---

## 2. Registration Endpoint

### Endpoint

```
POST /v1/auth/register
```

Lives in `lib/api/routes/auth.py` (already `_PUBLIC_ROUTER = True` — no Bearer required).

### Request body

```python
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
```

### Behavior

1. Call `user_service.create_user(username, email, password)` — reuses the existing method
2. New accounts are created with `is_active=True` (active immediately, no email verification)
3. Return `201 Created`

### Response

```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "alice",
  "is_active": true
}
```

### Error cases

| Condition | HTTP status | Detail |
|---|---|---|
| Username already taken | 409 | `"Username already registered"` |
| Email already registered | 409 | `"Email already registered"` |
| Validation failure (empty fields) | 422 | Pydantic auto |

`UserService.create_user` already raises on duplicate username — catch and convert to 409 in the route handler.

---

## 3. Password Reset

### PasswordResetToken Model — `lib/models/password_reset_token.py`

```python
from datetime import datetime, timezone
import uuid
from sqlalchemy import ForeignKey, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from lib.database.base import Base

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

Token is a 32-byte hex string (`secrets.token_hex(32)` = 64 chars). Not a UUID — opaque string is harder to enumerate.

### PasswordResetTokenRepository — `lib/repositories/password_reset_token_repository.py`

Three methods:

```python
class PasswordResetTokenRepository(AbstractRepository[PasswordResetToken]):
    model = PasswordResetToken

    def create_for_user(self, user_id: uuid.UUID, ttl_seconds: int = 900) -> str:
        """Create a new reset token. Returns the raw token string."""
        ...

    def find_valid(self, token: str) -> dict | None:
        """Return serialized token row if token exists, not used, and not expired. None otherwise."""
        ...

    def mark_used(self, token_id: uuid.UUID) -> None:
        """Set used_at = now on the given token row."""
        ...
```

`find_valid` checks: `used_at IS NULL AND expires_at > now()` — both conditions required.

### UserService methods

Two new methods on `UserService`:

```python
def request_reset(self, data: dict) -> dict:
    """
    data: {"email": "alice@example.com"}
    Finds user by email, creates a reset token, returns token + expiry.
    Returns success=True even if email not found (prevents user enumeration).
    """

def reset_password(self, data: dict) -> dict:
    """
    data: {"token": "abc123...", "new_password": "hunter2"}
    Validates token, hashes new password via security_service.hash_password()
    (same path as create_user), updates user, marks token used.
    Raises ValueError on invalid/expired token.
    """
```

`request_reset` always returns `{"token": "...", "expires_in": 900}` if email exists, or `{"message": "If that email is registered, a reset token has been issued"}` if not found — prevents user enumeration.

### Endpoints

Both in `lib/api/routes/auth.py` (public sub-router):

```
POST /v1/auth/forgot-password
  Body: {"email": "alice@example.com"}
  Response 200: {"token": "<64-char hex>", "expires_in": 900}
  Response 200 (email not found): {"message": "If that email is registered, a reset token has been issued"}

POST /v1/auth/reset-password
  Body: {"token": "<64-char hex>", "new_password": "newpass123"}
  Response 200: {"success": true}
  Response 400: {"detail": "Invalid or expired reset token"}
```

Token TTL is 15 minutes (900 seconds). Configurable via `UserService` constructor default — no new env var needed for now.

---

## 4. Pagination

### PaginatedResult contract — `lib/contracts/base.py`

Add alongside `ActionRequest`, `ActionResult`, `Event`:

```python
class PaginatedResult(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    pages: int
```

`pages = math.ceil(total / page_size)` — computed, not stored.

### AbstractRepository — `lib/repositories/base.py`

New method alongside `list()`:

```python
def list_paginated(
    self, page: int = 1, page_size: int = 20, **filters
) -> tuple[list[T], int]:
    """
    Returns (items, total_count).
    items: one page of results, already expunged.
    total_count: total matching rows across all pages.
    """
    with self._factory.session() as s:
        q = s.query(self.model)
        for k, v in filters.items():
            q = q.filter(getattr(self.model, k) == v)
        total = q.count()
        offset = (page - 1) * page_size
        rows = q.offset(offset).limit(page_size).all()
        for r in rows:
            s.expunge(r)
        return rows, total
```

`list()` is unchanged — existing callers unaffected.

### GET /v1/users — `lib/api/routes/users.py`

```python
@router.get("/")
def list_users(
    page: int = 1,
    page_size: int = 20,
    repo: UserRepository = Depends(get_repo),
):
    rows, total = repo.list_paginated(page=page, page_size=page_size)
    return {
        "items": [_serialize(u) for u in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }
```

`_serialize` is the same helper already used by `get_user`. The existing `GET /v1/users/{id}` endpoint is unchanged.

---

## Migration

One Alembic migration covers both schema changes:

```bash
alembic revision --autogenerate -m "add is_active to users and password_reset_tokens table"
alembic upgrade head
```

**Required:** `lib/database/migrations/env.py` must import `PasswordResetToken` so Alembic sees it:

```python
import lib.models.password_reset_token  # noqa: F401
```

---

## Test Coverage

### `tests/test_auth_gaps.py` (new file)

| Test | What it verifies |
|---|---|
| `test_register_creates_user` | POST /register → 201, user_id in response |
| `test_register_duplicate_username_409` | Second register same username → 409 |
| `test_register_duplicate_email_409` | Second register same email → 409 |
| `test_is_active_false_blocks_login` | Set is_active=False, login → 401 |
| `test_is_active_true_allows_login` | Default is_active=True, login succeeds |
| `test_forgot_password_returns_token` | POST /forgot-password → token in response |
| `test_forgot_password_unknown_email` | Unknown email → 200 with generic message (no 404) |
| `test_reset_password_success` | Valid token → password changed, login with new pass works |
| `test_reset_password_expired_token` | Expired token → 400 |
| `test_reset_password_used_token` | Already-used token → 400 |

### `tests/test_pagination.py` (new file)

| Test | What it verifies |
|---|---|
| `test_list_paginated_returns_metadata` | GET /v1/users?page=1&page_size=2 → total, pages fields present |
| `test_list_paginated_correct_total` | Create 5 users, total=5 |
| `test_list_paginated_page_2` | page=2 returns second set of items |
| `test_list_paginated_empty` | No users → items=[], total=0, pages=0 |

---

## What Is Not In This Spec

- Email delivery for reset tokens (token returned in response body)
- Role-based activation (admin activating accounts)
- Account lockout after failed attempts
- Refresh tokens / token rotation
- Pagination on any endpoint other than `GET /v1/users` (other endpoints can adopt the pattern independently)
