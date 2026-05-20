---
title: "Docker & Deployment"
category: guide
audience: [developer]
related:
  - ../core/ARCHITECTURE.md
  - ../reference/VAULT_USAGE.md
agent_priority: low
---

# Docker & Deployment Guide

FlexTemplates ships with a Docker-ready API-only mode. The Flet desktop UI stays
off when `API_ONLY=true` — only the FastAPI server runs. This is how you deploy
the backend to a container or a cloud environment.

---

## Quick Start — Docker Compose

```bash
# 1. Copy the env template
cp .env.example .env

# 2. Fill in the required secrets (see .env.example for all fields)
#    At minimum: JWT_SECRET_KEY, VAULT_MASTER_KEY, VAULT_CONFIRM_KEY

# 3. Start everything
docker compose up --build

# API is live at http://localhost:8080
# Docs at http://localhost:8080/docs
```

`docker-compose.yml` starts three services:

| Service | Purpose |
|---|---|
| `app` | FlexTemplates API (Python 3.12-slim, API_ONLY=true) |
| `db` | PostgreSQL 16 (registered as `"postgres"` in `ConnectionRegistry`) |
| `redis` | Redis 7 (registered as `"redis"` in `CacheRegistry`) |

---

## Required Environment Variables

Copy `.env.example` to `.env` and fill in every value marked `CHANGE_ME`:

```dotenv
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
VAULT_MASTER_KEY=CHANGE_ME
VAULT_CONFIRM_KEY=CHANGE_ME

# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=CHANGE_ME

# Database — already wired in docker-compose.yml; override for external DBs
DATABASE_URL=postgresql://flex:flex@db:5432/flex

# Optional Redis
REDIS_URL=redis://redis:6379/0
```

The server **hard-fails at startup** if `JWT_SECRET_KEY` is still the default
`dev-secret-change-in-production` when `API_ONLY=true`. This prevents accidentally
deploying with a forgeable signing key.

---

## How API-Only Mode Works

`AppConfig` reads the `API_ONLY` environment variable (default `false`):

```python
# lib/config/settings.py
api_only: bool = False   # Set API_ONLY=true to skip Flet UI
```

When `True`, `main.py` skips `ft.run()` and instead waits for SIGTERM/SIGINT:

```python
if config.api_only:
    signal.signal(signal.SIGTERM, lambda *_: _stop.set())
    _stop.wait()   # blocks until Docker sends SIGTERM
else:
    ft.run(main=flet_main)
```

Uvicorn, the scheduler, and all registered services start exactly the same in both
modes. Only the Flet window is suppressed.

---

## Vault in API-Only Mode

The vault design requires the **frontend to provide the master password**. In
headless/Docker mode there is no frontend — the master key comes from the
`VAULT_MASTER_KEY` environment variable instead (set in `.env` or as a Docker
secret).

Never commit `.env` or `.secrets/` to git. The `.dockerignore` excludes both.

To populate the vault before running the container:

```bash
# On the developer machine (not inside Docker)
flex-encrypt
# Enter keys interactively; they're encrypted and written to .secrets/vault.json

# Mount .secrets/ as a Docker volume (already wired in docker-compose.yml):
# volumes:
#   - .secrets:/app/.secrets
```

---

## Dockerfile Details

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir . && pip install --no-cache-dir psycopg2-binary
COPY . .
ENV PYTHONPATH=/app
ENV API_ONLY=true
RUN useradd -m appuser
USER appuser
EXPOSE 8080
CMD ["python", "main.py"]
```

Key decisions:
- **Non-editable install** (`pip install .`) — appropriate for immutable containers.
- **Non-root user** — `appuser` runs the process; no root privileges at runtime.
- **`.dockerignore`** — excludes `.secrets/`, `.env`, `*.db`, `.git`, `tests/`,
  and `__pycache__/` so secrets are never baked into image layers.

---

## Structured Logging

In API-only mode every log line is JSON, ready for ingestion by Datadog, Loki,
CloudWatch, or any log aggregator:

```json
{"ts": "2026-05-20 12:34:56,789", "level": "INFO", "logger": "flex.http",
 "msg": "GET /users 200", "method": "GET", "path": "/users", "status": 200, "ms": 4.2}
```

`setup_logging()` is called at startup with `DEBUG` level when `config.debug=true`,
`INFO` otherwise. Extra fields passed via `extra={}` are merged into the JSON object.

---

## Background Tasks

`TaskScheduler` wraps APScheduler and runs in the same process:

```python
# main.py — already wired
scheduler = TaskScheduler()
scheduler.start()

# Add jobs anywhere that has access to the scheduler:
scheduler.add_job(my_cleanup_fn, trigger="cron", hour=3)
scheduler.add_job(my_heartbeat_fn, trigger="interval", minutes=5)
```

The scheduler is stopped cleanly in the `finally` block when the server shuts down.

---

## CLI Vault Tools

Manage secrets from the command line without running the app:

```bash
# Add / update secrets (interactive)
flex-encrypt

# Print all secrets (dev only — prints a warning)
flex-decrypt
```

Both commands read `VAULT_PATH` and `VAULT_ENV_PATH` from the environment (or
use the defaults `.secrets/vault.json` and `.secrets/.env`).

---

## Deployment Checklist

- [ ] `.env` created from `.env.example` with real secrets
- [ ] `JWT_SECRET_KEY` set to a random 32-byte URL-safe base64 string
- [ ] `VAULT_MASTER_KEY` and `VAULT_CONFIRM_KEY` set and stored securely
- [ ] `DATABASE_URL` points to production DB
- [ ] `.secrets/vault.json` populated via `flex-encrypt` and mounted as a volume
- [ ] `.gitignore` includes `.env` and `.secrets/` (already in repo)
- [ ] `docker compose up --build` succeeds locally before pushing to CI
