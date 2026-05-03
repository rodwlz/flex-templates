"""SchemaInspector: introspect database schema metadata via SQLAlchemy reflection."""
from sqlalchemy import inspect
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory


class SchemaInspector(SimpleService):
    """Service for inspecting database schema metadata.

    Uses SQLAlchemy's inspect() API to reflect table and column information
    without requiring ORM models.

    Actions:
        - get_tables: returns list of all table names
        - get_schema: returns columns and metadata for a specific table
    """

    def __init__(self, factory: SessionFactory):
        """Initialize with a SessionFactory.

        Args:
            factory: SessionFactory with _engine attribute
        """
        self._factory = factory

    def get_tables(self, data: dict) -> dict:
        """Get list of all table names in the database.

        Args:
            data: unused

        Returns:
            dict with key "tables": list of table names
        """
        inspector = inspect(self._factory._engine)
        table_names = inspector.get_table_names()
        return {"tables": table_names}

    def get_schema(self, data: dict) -> dict:
        """Get columns and metadata for a specific table.

        Args:
            data: must contain "table_name" key

        Returns:
            dict with keys "table" (name) and "columns" (list of column dicts)

        Raises:
            KeyError: if table_name not in data
            Exception: if table doesn't exist or can't be inspected
        """
        table_name = data["table_name"]
        inspector = inspect(self._factory._engine)

        # get_columns raises an exception if table doesn't exist
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint["constrained_columns"]) if pk_constraint else set()

        # Enrich column metadata
        result_columns = []
        for col in columns:
            result_columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "primary_key": col["name"] in pk_columns,
                "default": str(col["default"]) if col.get("default") is not None else None,
            })

        return {"table": table_name, "columns": result_columns}
