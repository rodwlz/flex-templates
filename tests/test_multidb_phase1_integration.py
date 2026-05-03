"""
Phase 1 Multi-Database Integration Test: Full Workflow.

This integration test validates the complete workflow:
    1. AppConfig loads DATABASE_* environment variables
    2. Multiple databases registered with ConnectionRegistry
    3. ConnectionTester verifies both connections are alive
    4. SchemaInspector inspects tables and schema from both databases

The test simulates a real-world scenario: two independent SQLite databases
(main and analytics) each with sample tables, registered at startup, tested for
connectivity, and inspected for schema metadata.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.config.settings import AppConfig
from lib.database.session import SessionFactory, ConnectionRegistry
from lib.services.schema_inspector import SchemaInspector
from lib.services.connection_tester import ConnectionTester
from lib.contracts.base import ActionRequest


@pytest.fixture(autouse=True)
def clean_connection_registry():
    """Clear the ConnectionRegistry before and after each test."""
    ConnectionRegistry._factories = {}
    yield
    ConnectionRegistry._factories = {}


def _create_shared_memory_factory(url: str) -> SessionFactory:
    """Create an in-memory SQLite factory with StaticPool (required for thread sharing).

    This is similar to the pattern in test_api.py, ensuring that the session
    pool keeps one connection alive so the schema creation and subsequent
    queries see the same in-memory database.
    """
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def main_db_factory():
    """Create the 'main' database with users and products tables."""
    factory = _create_shared_memory_factory("sqlite:///:memory:")

    # Create users table
    with factory.session() as session:
        session.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """))
        session.execute(text("""
            INSERT INTO users (username, email, created_at)
            VALUES ('alice', 'alice@example.com', '2025-01-01T00:00:00')
        """))

    return factory


@pytest.fixture
def analytics_db_factory():
    """Create the 'analytics' database with events and metrics tables."""
    factory = _create_shared_memory_factory("sqlite:///:memory:")

    # Create events table
    with factory.session() as session:
        session.execute(text("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """))
        session.execute(text("""
            CREATE TABLE metrics (
                id INTEGER PRIMARY KEY,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                date TEXT NOT NULL
            )
        """))
        session.execute(text("""
            INSERT INTO events (event_type, user_id, timestamp)
            VALUES ('login', 1, '2025-01-01T12:00:00')
        """))
        session.execute(text("""
            INSERT INTO metrics (metric_name, value, date)
            VALUES ('daily_active_users', 42.0, '2025-01-01')
        """))

    return factory


class TestMultiDbPhase1Integration:
    """Full workflow integration test for multi-database Phase 1."""

    def test_full_workflow_config_registry_test_inspect(
        self, main_db_factory, analytics_db_factory, monkeypatch
    ):
        """
        End-to-end test: config → registry → test connections → inspect schemas.

        Steps:
            1. Simulate AppConfig loading DATABASE_MAIN and DATABASE_ANALYTICS
            2. Register both databases with ConnectionRegistry
            3. Test both connections are alive
            4. Inspect tables in main DB
            5. Inspect schema (columns) for 'users' table
            6. Inspect tables in analytics DB
            7. Inspect schema (columns) for 'events' table
        """
        # ── Step 1: Simulate AppConfig loading DATABASE_* env vars ─────────
        monkeypatch.setenv("DATABASE_MAIN", "sqlite:///:memory:")
        monkeypatch.setenv("DATABASE_ANALYTICS", "sqlite:///:memory:")

        config = AppConfig()
        assert "main" in config.databases
        assert "analytics" in config.databases

        # ── Step 2: Register both databases with ConnectionRegistry ────────
        # Directly register factories (bypassing URL parsing)
        ConnectionRegistry._factories["main"] = main_db_factory
        ConnectionRegistry._factories["analytics"] = analytics_db_factory

        main_factory = ConnectionRegistry.get("main")
        analytics_factory = ConnectionRegistry.get("analytics")

        assert main_factory is main_db_factory
        assert analytics_factory is analytics_db_factory

        # ── Step 3: Test both connections are alive ───────────────────────
        main_tester = ConnectionTester(main_factory)
        analytics_tester = ConnectionTester(analytics_factory)

        # Test main DB
        main_result = main_tester.execute(ActionRequest(action="test", data={}))
        assert main_result.success is True
        assert main_result.data["alive"] is True
        assert main_result.data["latency_ms"] >= 0
        assert main_result.data["error"] is None

        # Test analytics DB
        analytics_result = analytics_tester.execute(ActionRequest(action="test", data={}))
        assert analytics_result.success is True
        assert analytics_result.data["alive"] is True
        assert analytics_result.data["latency_ms"] >= 0
        assert analytics_result.data["error"] is None

        # ── Step 4: Inspect tables in main DB ──────────────────────────────
        main_inspector = SchemaInspector(main_factory)

        tables_result = main_inspector.execute(
            ActionRequest(action="get_tables", data={})
        )
        assert tables_result.success is True
        main_tables = tables_result.data["tables"]
        assert "users" in main_tables
        assert isinstance(main_tables, list)

        # ── Step 5: Inspect schema (columns) for 'users' table ─────────────
        schema_result = main_inspector.execute(
            ActionRequest(action="get_schema", data={"table_name": "users"})
        )
        assert schema_result.success is True
        assert schema_result.data["table"] == "users"
        assert "columns" in schema_result.data

        columns = schema_result.data["columns"]
        assert len(columns) > 0

        col_names = [col["name"] for col in columns]
        assert "id" in col_names
        assert "username" in col_names
        assert "email" in col_names
        assert "created_at" in col_names

        # Verify column metadata
        id_col = next(c for c in columns if c["name"] == "id")
        assert id_col["primary_key"] is True
        assert "type" in id_col

        username_col = next(c for c in columns if c["name"] == "username")
        assert username_col["nullable"] is False

        # ── Step 6: Inspect tables in analytics DB ────────────────────────
        analytics_inspector = SchemaInspector(analytics_factory)

        tables_result = analytics_inspector.execute(
            ActionRequest(action="get_tables", data={})
        )
        assert tables_result.success is True
        analytics_tables = tables_result.data["tables"]
        assert "events" in analytics_tables
        assert "metrics" in analytics_tables

        # ── Step 7: Inspect schema (columns) for 'events' table ────────────
        schema_result = analytics_inspector.execute(
            ActionRequest(action="get_schema", data={"table_name": "events"})
        )
        assert schema_result.success is True
        assert schema_result.data["table"] == "events"

        columns = schema_result.data["columns"]
        col_names = [col["name"] for col in columns]
        assert "id" in col_names
        assert "event_type" in col_names
        assert "user_id" in col_names
        assert "timestamp" in col_names

        # ── Verify independence: main DB cannot see analytics tables ────────
        # If we ask main_inspector about 'events', it should fail gracefully
        missing_result = main_inspector.execute(
            ActionRequest(action="get_schema", data={"table_name": "events"})
        )
        assert missing_result.success is False

        # ── Verify independence: analytics DB cannot see main DB tables ─────
        missing_result = analytics_inspector.execute(
            ActionRequest(action="get_schema", data={"table_name": "users"})
        )
        assert missing_result.success is False

    def test_connection_registry_isolation(self, main_db_factory, analytics_db_factory):
        """ConnectionRegistry keeps databases isolated: each name returns correct factory."""
        ConnectionRegistry._factories["main"] = main_db_factory
        ConnectionRegistry._factories["analytics"] = analytics_db_factory

        # Each name returns the correct factory
        assert ConnectionRegistry.get("main") is main_db_factory
        assert ConnectionRegistry.get("analytics") is analytics_db_factory

        # Asking for a non-existent database raises RuntimeError
        with pytest.raises(RuntimeError, match="No database registered"):
            ConnectionRegistry.get("nonexistent")

    def test_schema_inspector_handles_missing_database(self, main_db_factory):
        """SchemaInspector gracefully handles errors via ActionResult.success=False."""
        inspector = SchemaInspector(main_db_factory)

        result = inspector.execute(
            ActionRequest(action="get_schema", data={"table_name": "nonexistent_table"})
        )

        assert result.success is False
        assert result.error is not None

    def test_connection_tester_measures_latency(self, main_db_factory):
        """ConnectionTester measures and returns reasonable latency."""
        tester = ConnectionTester(main_db_factory)
        result = tester.execute(ActionRequest(action="test", data={}))

        assert result.success is True
        latency_ms = result.data["latency_ms"]

        # Latency should be positive and reasonable for in-memory SQLite
        assert isinstance(latency_ms, (int, float))
        assert latency_ms >= 0
        assert latency_ms < 1000  # Should be < 1 second
