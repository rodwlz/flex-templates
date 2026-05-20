---
title: "Testing Patterns"
category: reference
audience: [developer, agent]
related:
  - ../core/CONVENTIONS.md
  - ../guides/API_DEVELOPMENT.md
agent_priority: medium
---

# Testing — When You Break Stuff

You will break things. That's fine. The tests are here to tell you *what* you broke so you don't have to guess.

---

## Run the tests

```bash
pytest tests/ -v
```

Pass any pytest flag:

```bash
pytest tests/ -v                            # verbose, one line per test
pytest tests/ -x                            # stop at first failure
pytest tests/test_router.py                 # only one file
pytest tests/ -k "back_button"             # only tests matching "back_button"
pytest tests/ --tb=short -q               # quiet with short tracebacks
```

---

## What gets tested

### Core framework

| File | What it checks |
| --- | --- |
| `test_contracts.py` | `ActionRequest` / `ActionResult` / `Event` shapes are stable |
| `test_event_bus.py` | Subscribe / publish / unsubscribe wiring |
| `test_interfaces.py` | `SimpleService` dispatch, exception wrapping, `StagingService` flows |
| `test_navigation_service.py` | Browser-like history (visit, back, forward) |
| `test_router.py` | URL resolution, named routes, query strings, caching |
| `test_base_view.py` | Layout toggles, swappable parts, typed params |
| `test_smoke.py` | "Does the whole app even boot?" — imports every new module |

### Data layer

| File | What it checks |
| --- | --- |
| `test_session.py` | `SessionFactory.session()` commit / rollback semantics |
| `test_repository_base.py` | `AbstractRepository[T]` CRUD + `paginate()` + `filter_by()` |
| `test_repositories.py` | `UserRepository` with real ORM model |
| `test_uow.py` | `UnitOfWork` stage / preview / commit / rollback |

### Services

| File | What it checks |
| --- | --- |
| `test_services.py` | `UserService` create, get, list, delete, authenticate |
| `test_vault_service.py` | Vault unlock / get / set / save / lock round-trip |
| `test_settings.py` | `AppConfig` env-var loading, `api_only` flag |

### Auth & security

| File | What it checks |
| --- | --- |
| `test_password.py` | bcrypt `hash_password` / `verify_password` |
| `test_jwt.py` | JWT create / decode / expiry / invalid-token errors |
| `test_auth_api.py` | `POST /auth/login` happy path and failure cases |
| `test_rbac.py` | `get_current_user`, `require_roles`, 401/403 responses |

### API routes

| File | What it checks |
| --- | --- |
| `test_api.py` | User and role CRUD endpoints, UUID path params, 404s |
| `test_api_routes.py` | Role CRUD, user/role association, staged operations |
| `test_mount_service.py` | `mount_service()` auto-generates routes from `SimpleService` |

### Repository extensions

| File | What it checks |
| --- | --- |
| `test_repository_base.py` | `paginate()` page/size/total + `filter_by()` Django-style ops |

### Infrastructure

| File | What it checks |
| --- | --- |
| `test_logging_middleware.py` | `JsonFormatter`, `log_requests` HTTP middleware |
| `test_scheduler.py` | `TaskScheduler` add/start/stop lifecycle |
| `test_cli_vault.py` | `flex-encrypt` / `flex-decrypt` vault round-trips |

---

## Reading a failure

When a test fails, pytest tells you three things:

1. **Which test** failed (file + name)
2. **What it expected** vs **what it got**
3. **The traceback** — read from the bottom up

Example:

```text
FAILED tests/test_smoke.py::test_route_renders_without_errors[/products/1]
    AttributeError: module 'lib.views.product_detail' has no attribute 'view'
```

That tells you: someone renamed or deleted the `view()` function in `product_detail.py`. Go look at line 1 of that file.

---

## The 5 failures you'll hit most often

### 1. `AttributeError: module 'lib.views.X' has no attribute 'view'`

You forgot the `view()` function at the bottom of your view file:

```python
def view(page, props):
    return MyView(page, props).render()
```

### 2. `KeyError: 'nav_service'`

You called `props["nav_service"]` but `set_props_factory` in [main.py](../main.py) doesn't include it. Add the service to the factory.

### 3. `pydantic.ValidationError`

Your URL has a value that doesn't match your `Params` model.

- `/products/abc` when `id: int` → `abc` isn't an int.
- Fix: either change the URL or relax the type to `id: str`.

### 4. `NotImplementedError: ...build_content() must be implemented`

You created a `BaseView` subclass but forgot to override `build_content()`. Every view must have one.

### 5. `TypeError: Button.__init__() got an unexpected keyword argument 'text'`

Flet 0.84+ uses `content=` not `text=` for most controls. Same goes for `ft.PopupMenuItem` — pass `content=ft.Text("…")` instead of `text="…"`. Replace `ft.ElevatedButton(text="Hi")` with `ft.ElevatedButton("Hi")`.

---

## Adding a test for new code

1. Find the file in `tests/` that matches what you're testing (or create a new `test_<thing>.py`).
1. Write a function whose name starts with `test_` and reads like a sentence:

    ```python
    def test_back_button_calls_nav_service_back(nav_service):
        # Setup
        button = BackButton(nav_service)

        # Action — simulate a click
        button.on_click(None)

        # Check
        assert nav_service.current == "/"  # we went back to homepage
    ```

1. Use the existing fixtures (`event_bus`, `nav_service`, `router`, `fake_page`) from [conftest.py](../tests/conftest.py) instead of re-wiring everything yourself.

That's it. No mocking framework, no async dance, no fixtures factory. Plain Python, plain assertions.

---

## When tests pass but the app is still broken

Tests check logic. They can't see:

- Visual glitches (colors, alignment, missing icons)
- Performance issues
- Network calls that fail in production
- Anything you didn't write a test for

If `pytest` is green but the UI looks wrong, **that's not pytest's fault** — that's a missing test. Add one.
