"""SchemaInspector service: inspect database schema metadata via SQLAlchemy reflection."""
import pytest
from lib.database.session import SessionFactory
from lib.database.base import Base
from lib.services.schema_inspector import SchemaInspector
from lib.contracts.base import ActionRequest


@pytest.fixture
def schema_inspector(db_factory):
    """Create a SchemaInspector with a test database."""
    return SchemaInspector(db_factory)


def test_get_tables_returns_table_list(schema_inspector):
    """SchemaInspector.get_tables() returns list of table names."""
    result = schema_inspector.execute(ActionRequest(action="get_tables", data={}))
    assert result.success is True
    assert "tables" in result.data
    assert isinstance(result.data["tables"], list)
    # Should include the users table from Base
    assert "users" in result.data["tables"]


def test_get_schema_returns_columns_and_types(schema_inspector):
    """get_schema() returns columns with types and constraints."""
    result = schema_inspector.execute(
        ActionRequest(action="get_schema", data={"table_name": "users"})
    )
    assert result.success is True
    assert result.data["table"] == "users"
    assert "columns" in result.data
    assert isinstance(result.data["columns"], list)

    # Check that we have User model columns
    col_names = [col["name"] for col in result.data["columns"]]
    assert "id" in col_names
    assert "username" in col_names
    assert "email" in col_names
    assert "password_hash" in col_names

    # Check that columns have type information
    id_col = next(c for c in result.data["columns"] if c["name"] == "id")
    assert "type" in id_col
    assert "primary_key" in id_col


def test_get_schema_handles_missing_table(schema_inspector):
    """get_schema() gracefully handles invalid table name."""
    result = schema_inspector.execute(
        ActionRequest(action="get_schema", data={"table_name": "nonexistent"})
    )
    assert result.success is False
    assert result.error is not None


def test_get_schema_requires_table_name(schema_inspector):
    """get_schema() errors when table_name not in data."""
    result = schema_inspector.execute(ActionRequest(action="get_schema", data={}))
    assert result.success is False
    assert result.error is not None
