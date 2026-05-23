import os
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

from lib.database.base import Base
import lib.models.user  # noqa: F401 — registers User on Base.metadata
import lib.models.role  # noqa: F401 — registers Role on Base.metadata
import lib.models.password_reset_token  # noqa: F401 — registers PasswordResetToken
import lib.models.product  # noqa: F401 — registers Product on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    # Priority: DATABASE_URL env var → named ConnectionRegistry entry → alembic.ini fallback
    # Set DATABASE_URL to target any database (SQLite path, postgres:// URL, etc.)
    # Set DATABASE_NAME to use a named registry entry when the app is already booted.
    if url := os.getenv("DATABASE_URL"):
        return url
    try:
        from lib.database.session import ConnectionRegistry
        name = os.getenv("DATABASE_NAME", "default")
        return str(ConnectionRegistry.get(name)._engine.url)
    except Exception:
        return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_get_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
