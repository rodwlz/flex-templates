# Testing — When You Break Stuff

You will break things. That's fine. The tests are here to tell you *what* you broke so you don't have to guess.

---

## Run the tests

**Windows:** Double-click `test.bat`.

**Any platform** (Windows / macOS / Linux), from the terminal:

```bash
python run_test.py
```

Pass any pytest flag through:

```bash
python run_test.py -v                       # verbose, one line per test
python run_test.py -x                       # stop at first failure
python run_test.py tests/test_router.py     # only one file
python run_test.py -k "back_button"         # only tests matching "back_button"
```

---

## What gets tested

| File | What it checks |
| --- | --- |
| `test_contracts.py` | `ActionRequest` / `ActionResult` / `Event` shapes are stable |
| `test_event_bus.py` | Subscribe / publish / unsubscribe wiring |
| `test_navigation_service.py` | Browser-like history (visit, back, forward) |
| `test_router.py` | URL resolution, named routes, query strings, caching |
| `test_base_view.py` | Layout toggles, swappable parts, typed params |
| `test_smoke.py` | "Does the whole app even boot?" — runs after every change |

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
