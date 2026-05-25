"""
run_migrations — thin wrapper around Alembic's upgrade command.

Use this instead of create_tables() for any project that has a migrations/
directory. create_tables() uses metadata.create_all which drifts from Alembic
state over time; run_migrations() always applies the exact recorded revisions.

Usage in main.py:
    from lib.database.migrations import run_migrations
    run_migrations()                          # uses alembic.ini in project root
    run_migrations("path/to/alembic.ini")     # custom location
"""
from __future__ import annotations


def run_migrations(alembic_cfg_path: str = "alembic.ini") -> None:
    """Run all pending Alembic migrations (equivalent to `alembic upgrade head`).

    Safe to call on every startup — Alembic is a no-op when already at head.
    Raises SystemExit / alembic exceptions on failure; let them propagate so the
    app does not start with a mismatched schema.
    """
    from alembic.config import Config
    from alembic import command

    cfg = Config(alembic_cfg_path)
    command.upgrade(cfg, "head")
