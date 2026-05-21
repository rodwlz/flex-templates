# Phase 5A — Framework Hygiene

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two symmetric repository hooks (`_serialize` / `_deserialize`) and a typed `ViewContext` dataclass — zero breakage, immediate ergonomic gain for every entity added after this.

**Architecture:** Pure additions. `AbstractRepository` gets overridable hooks that existing methods route through. `BaseView` gains a typed `self.ctx` alongside the existing untyped `self.props`. No existing view, service, or test needs to change.

**Tech Stack:** Python dataclasses, SQLAlchemy `inspect`, existing framework patterns.

---

## Part 1 — Repository Hooks

### The problem

`paginate()` and `filter_by()` call a module-level `_obj_to_dict()` that only serializes scalar columns. Any entity with relationships (User → roles, Order → items) must override the entire `paginate()` method — 15+ lines — just to add one relationship field. `UserRepository` already does this. Every future entity will repeat it.

The inbound side is worse: `create()` does `self.model(**data)` directly. If a form or API payload includes an unknown key, SQLAlchemy raises a cryptic `TypeError`. UUID strings arrive from views as `str` but the model expects `uuid.UUID` — callers handle this themselves, inconsistently.

### Design

Two instance methods on `AbstractRepository`, both overridable:

```python
def _serialize(self, obj: T) -> dict:
    """Outbound: ORM object → dict. Override to add relationship fields."""
    return {c.key: getattr(obj, c.key)
            for c in sa_inspect(obj).mapper.column_attrs}

def _deserialize(self, data: dict) -> dict:
    """Inbound: strip unknown keys. Override to add type coercion on top."""
    known = {c.key for c in sa_inspect(self.model).mapper.column_attrs}
    return {k: v for k, v in data.items() if k in known}
```

**Outbound flow** — `paginate()` and `filter_by()` call `self._serialize(row)` instead of `_obj_to_dict(row)`. Called while the session is still open, so lazy-loaded relationships are accessible.

**Inbound flow** — `create()` and `update()` call `self._deserialize(data)` before touching the model. Unknown keys are silently dropped. Subclasses call `super()._deserialize(data)` first, then coerce types.

### UserRepository after the change

```python
class UserRepository(AbstractRepository[User]):
    model = User

    def _serialize(self, obj) -> dict:
        d = super()._serialize(obj)
        d["roles"] = [r.name for r in obj.roles]
        return d

    def _deserialize(self, data: dict) -> dict:
        d = super()._deserialize(data)          # strips unknown keys
        for field in ("id", "user_id"):
            if field in d and isinstance(d[field], str):
                d[field] = uuid.UUID(d[field])
        return d
```

The current 20-line `paginate()` override is deleted entirely.

### Pattern for future entities

Any new entity with relationships overrides `_serialize()`. Any entity receiving UUID strings from forms overrides `_deserialize()`. Neither requires touching pagination logic.

---

## Part 2 — ViewContext

### The problem

Every view extracts props by string key: `self._backend = props.get("backend")`. No IDE help, no documentation of what's available, silent `None` on typos. The full set of injectable props is only discoverable by reading `main.py`.

### Design

New file `lib/contracts/view_context.py` — a dataclass that wraps the props dict:

```python
@dataclass
class ViewContext:
    nav_service: Any    # NavigationService
    backend:     Any    # IBackendAdapter | None
    nav:         Any    # NavigationService simple wrapper | None
    vault:       Any    # Vault | None
    events:      Any    # EventBus | None
    dev_nav:     bool
    params:      dict
    query:       dict

    @classmethod
    def from_props(cls, props: dict) -> "ViewContext":
        return cls(
            nav_service = props["nav_service"],
            backend     = props.get("backend"),
            nav         = props.get("nav"),
            vault       = props.get("vault"),
            events      = props.get("events"),
            dev_nav     = bool(props.get("dev_nav")),
            params      = props.get("params", {}),
            query       = props.get("query", {}),
        )
```

`Any` types now — real types would import from adapters/services and create circular deps. Phase 5B fills them in after the adapter is split. The win at this stage is that `self.ctx.backend` is a documented, autocompletable attribute.

`BaseView.__init__` adds one line after the existing nav extraction:

```python
self.ctx = ViewContext.from_props(props)
```

`self.props` is untouched. Old views work unchanged. New views use `self.ctx`.

---

## Part 3 — Auth Login Delay

### The problem

The `/auth/login` endpoint currently returns `401` immediately on bad credentials. A password guesser can attempt thousands of tries per second.

### Design

Add `await asyncio.sleep(0.5)` (async route) or `time.sleep(0.5)` (sync) in the `401` branch of the login route. This is not rate limiting — it's a constant penalty on every failed attempt that makes brute-force impractical without affecting legitimate users (one failure costs 500ms; success is unaffected).

---

## Files

| File | Action |
|---|---|
| `lib/repositories/base.py` | Add `_serialize()`, `_deserialize()`; update `paginate()`, `filter_by()`, `create()`, `update()` |
| `lib/repositories/user_repository.py` | Replace `paginate()` override with `_serialize()` + `_deserialize()` |
| `lib/contracts/view_context.py` | Create — `ViewContext` dataclass |
| `lib/ui/layouts/base_view.py` | Add `self.ctx = ViewContext.from_props(props)` |
| `lib/api/routes/auth.py` | Add 500ms delay on failed login |
| `tests/test_repository_base.py` | Add `_serialize` and `_deserialize` tests |
| `tests/test_base_view.py` | Add `ctx` attribute tests |
| `tests/test_smoke.py` | Add `lib.contracts.view_context` import |

---

## Tests

### Repository hooks

```
test_serialize_returns_scalar_columns_only
    — base _serialize() does not include relationship attrs

test_serialize_subclass_adds_relationships
    — UserRepository._serialize() includes roles list

test_deserialize_strips_unknown_keys
    — base _deserialize() drops keys not on the model

test_deserialize_keeps_known_keys
    — known column keys pass through unchanged

test_deserialize_subclass_coerces_uuid
    — UserRepository._deserialize() converts "id" str to uuid.UUID

test_create_strips_unknown_via_deserialize
    — create({"username": "x", "unknown_field": "y"}) succeeds, unknown_field ignored

test_update_strips_unknown_via_deserialize
    — update(id, {"email": "new@x.com", "junk": True}) updates only email

test_paginate_uses_serialize_hook
    — paginate() result items include roles when UserRepository used

test_filter_by_uses_serialize_hook
    — filter_by() result dicts include custom serialized fields
```

### ViewContext

```
test_view_context_from_props_extracts_all_keys
    — from_props() with full props dict populates all fields

test_view_context_missing_optional_keys_default_to_none
    — props with only nav_service sets backend=None etc.

test_base_view_exposes_ctx
    — BaseView instance has .ctx attribute of type ViewContext

test_base_view_ctx_backend_matches_props
    — ctx.backend is same object as props["backend"]

test_existing_props_dict_still_works
    — self.props["nav_service"] still accessible after adding ctx
```

### Auth delay

```
test_failed_login_takes_at_least_500ms
    — time the 401 response; assert elapsed >= 0.45s

test_successful_login_is_not_delayed
    — time the 200 response; assert elapsed < 0.5s
```
