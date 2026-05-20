"""
AppConfig — single source of truth for app configuration.

Replaces scattered os.getenv() calls. Priority: env vars > .env file > defaults.

Usage:
    from lib.config.settings import AppConfig
    config = AppConfig()
    server.start(host=config.api_host, port=config.api_port)

    # Database URLs are loaded from DATABASE_* env vars:
    # export DATABASE_MAIN=postgresql://localhost/db
    # config.databases["main"] == "postgresql://localhost/db"
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    # ── HTTP server (Phase 4) ──────────────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 8080

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./dev.db"
    postgres_url: str = ""
    databases: dict[str, str] = {}

    # ── Vault / secrets ────────────────────────────────────────────────────
    vault_master_key: str = ""
    vault_confirm_key: str = ""
    vault_path: str = ".secrets/vault.json"
    vault_env_path: str = ".secrets/.env"

    # ── UI ─────────────────────────────────────────────────────────────────
    app_title: str = "FlexTemplates"
    debug: bool = False

    # ── Deployment ─────────────────────────────────────────────────────────
    api_only: bool = False  # Set API_ONLY=true in Docker to skip Flet UI

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **data):
        """Initialize AppConfig and auto-populate databases from DATABASE_* env vars."""
        super().__init__(**data)
        # Auto-populate databases dict from DATABASE_* environment variables
        self.databases = self._load_databases_from_env()

    def _load_databases_from_env(self) -> dict[str, str]:
        """
        Scan environment for DATABASE_* variables and return as {name: url} dict.

        Merges os.environ (real env) with .env file values so that DATABASE_*
        entries work whether set in the shell or in .env.

        Example:
            DATABASE_MAIN=postgresql://localhost/db → {"main": "postgresql://localhost/db"}
            DATABASE_NORTHWIND=mssql+pyodbc://...  → {"northwind": "..."}
        """
        # pydantic-settings reads .env into model fields but does NOT inject into
        # os.environ — read the .env file directly so DATABASE_* lines work there too.
        env: dict[str, str] = dict(os.environ)
        env_file = str(self.model_config.get("env_file", ".env"))
        try:
            from dotenv import dotenv_values
            env.update(dotenv_values(env_file))
        except Exception:
            pass  # dotenv not installed or .env missing — fall back to os.environ only

        databases = {}
        prefix = "DATABASE_"
        for key, value in env.items():
            if key.startswith(prefix) and value:
                db_name = key[len(prefix):].lower()
                databases[db_name] = value
        return databases
