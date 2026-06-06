# Docker Integration Guide

## The Namespace Package Model

`flex-templates/lib/` is a Python **namespace package** — it has no `__init__.py`.
Your consumer project's `lib/` is also a namespace package (remove its `__init__.py`
if present). Python 3 then **merges both `lib/` trees automatically** at import time:

```
my-app/
  lib/           ← your domain code (views, services, models, ...)
  flex-templates/
    lib/          ← framework code (database/, adapters/, ui/, ...)
```

```python
# Both work in the same process — Python merges the lib/ namespace:
import lib.database.session      # from flex-templates/lib/
import lib.views.dashboard        # from my-app/lib/
```

**Requirement:** neither `lib/` directory may have `__init__.py`.
If your app has one, delete it. The namespace merge only fires when both sides are
namespace packages.

---

## Canonical Dockerfile (multi-stage, production-ready)

```dockerfile
# ── Stage 1: build deps ───────────────────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /build

# Copy only dependency files first (layer-cache friendly)
COPY flex-templates/pyproject.toml flex-templates/
COPY pyproject.toml .

# Install all runtime deps from both projects into one venv
RUN pip install --no-cache-dir \
      -e flex-templates/ \
      -e .

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Re-use the installed packages from stage 1
COPY --from=deps /usr/local/lib/python3.12/site-packages \
                 /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy source trees — namespace merge happens here
COPY flex-templates/lib ./flex-templates/lib
COPY lib ./lib
COPY main.py alembic.ini ./

# Optional: copy assets, migrations, etc.
COPY lib/assets ./lib/assets
COPY flex-templates/lib/database/migrations ./flex-templates/lib/database/migrations

# Tell Python where the namespace roots are
ENV PYTHONPATH="/app:/app/flex-templates"

# Run migrations then start the app
CMD ["sh", "-c", "alembic upgrade head && python main.py"]
```

### Key points

| Line | Why |
|---|---|
| `pip install -e flex-templates/ -e .` | Installs deps from both `pyproject.toml` files; `-e` keeps source editable so `COPY` below picks up actual files |
| `COPY flex-templates/lib ./flex-templates/lib` | Keeps the two `lib/` trees in separate paths on disk |
| `COPY lib ./lib` | Your domain code |
| `PYTHONPATH="/app:/app/flex-templates"` | Both paths are on `sys.path`; Python merges the `lib/` namespace packages |

---

## Local Development (no Docker)

Add both roots to `PYTHONPATH` or use `pyproject.toml` / `pytest.ini`:

```toml
# your-app/pyproject.toml
[tool.pytest.ini_options]
pythonpath = [".", "flex-templates"]
```

Or in your shell:

```bash
export PYTHONPATH="$PWD:$PWD/flex-templates"
python main.py
```

---

## Git Submodule Pattern

The recommended way to track flex-templates in a consumer project:

```bash
# Add once
git submodule add https://github.com/your-org/flex-templates.git flex-templates

# Pull framework updates
git submodule update --remote --merge
```

After pulling framework updates, check `CHANGELOG.md` in `flex-templates/` for any
breaking changes before merging.

---

## Common Pitfalls

### `ModuleNotFoundError: No module named 'lib.database'`

`flex-templates/` is not on `PYTHONPATH`. Add it:

```bash
export PYTHONPATH="$PWD:$PWD/flex-templates"
```

or set `pythonpath = [".", "flex-templates"]` in your `pyproject.toml`.

### `ImportError` after adding a repository to flex-templates

If flex-templates adds `lib/repositories/new_repo.py` after you forked, you won't
see it automatically. Consumer projects that have `lib/repositories/__init__.py`
(even an empty one) block the namespace merge for that sub-package. Delete the
`__init__.py` or explicitly import the new repo.

### `lib/__init__.py` exists in consumer project

Delete it. Any `__init__.py` in `lib/` turns it into a regular package and prevents
namespace merging — your consumer `lib/` will shadow framework `lib/` entirely.
