"""
Tests for AppConfig settings loading from environment variables.

Ensures DATABASE_* env vars are correctly loaded into the databases dict.
"""
import os
import pytest
from lib.config.settings import AppConfig


@pytest.fixture
def clean_env():
    """Clean up DATABASE_* env vars before and after each test."""
    # Store original values
    original_vars = {}
    for key in list(os.environ.keys()):
        if key.startswith("DATABASE_"):
            original_vars[key] = os.environ.pop(key)

    yield

    # Restore original values
    for key in list(os.environ.keys()):
        if key.startswith("DATABASE_"):
            del os.environ[key]
    for key, value in original_vars.items():
        os.environ[key] = value


def test_appconfig_loads_empty_databases_by_default(clean_env):
    """AppConfig.databases should be empty dict when no DATABASE_* vars are set."""
    config = AppConfig()
    assert config.databases == {}


def test_appconfig_loads_single_database_env_var(clean_env):
    """AppConfig should load DATABASE_MAIN from environment."""
    os.environ["DATABASE_MAIN"] = "postgresql://localhost/test_db"
    config = AppConfig()
    assert config.databases["main"] == "postgresql://localhost/test_db"


def test_appconfig_loads_multiple_database_env_vars(clean_env):
    """AppConfig should load multiple DATABASE_* vars into databases dict."""
    os.environ["DATABASE_MAIN"] = "postgresql://localhost/main_db"
    os.environ["DATABASE_ANALYTICS"] = "postgresql://localhost/analytics_db"
    os.environ["DATABASE_CACHE"] = "redis://localhost:6379"

    config = AppConfig()

    assert config.databases["main"] == "postgresql://localhost/main_db"
    assert config.databases["analytics"] == "postgresql://localhost/analytics_db"
    assert config.databases["cache"] == "redis://localhost:6379"
    assert len(config.databases) == 3


def test_appconfig_converts_database_keys_to_lowercase(clean_env):
    """DATABASE_UPPERCASE env var should become lowercase key in dict."""
    os.environ["DATABASE_PRODUCTION"] = "postgresql://prod/db"
    os.environ["DATABASE_DEV"] = "sqlite:///dev.db"

    config = AppConfig()

    assert "production" in config.databases
    assert "dev" in config.databases
    assert config.databases["production"] == "postgresql://prod/db"
    assert config.databases["dev"] == "sqlite:///dev.db"


def test_appconfig_ignores_non_database_env_vars(clean_env):
    """AppConfig should only include DATABASE_* vars, ignore others."""
    os.environ["DATABASE_MAIN"] = "postgresql://localhost/db"
    os.environ["API_HOST"] = "127.0.0.1"
    os.environ["VAULT_KEY"] = "secret"

    config = AppConfig()

    assert "main" in config.databases
    assert len(config.databases) == 1


def test_appconfig_databases_field_is_dict(clean_env):
    """AppConfig.databases field should be a dict type."""
    config = AppConfig()
    assert isinstance(config.databases, dict)
