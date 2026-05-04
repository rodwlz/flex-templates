from sqlalchemy import inspect
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory


class SchemaInspector(SimpleService):
    """
    Actions: get_tables, get_schema

    get_tables(data: {}) -> {tables: [str]}
    get_schema(data: {table_name}) -> {table, columns: [{name, type, nullable, primary_key, default}]}
    """

    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def get_tables(self, data: dict) -> dict:
        inspector = inspect(self._factory._engine)
        return {"tables": inspector.get_table_names()}

    def get_schema(self, data: dict) -> dict:
        table_name = data["table_name"]
        inspector = inspect(self._factory._engine)

        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint["constrained_columns"]) if pk_constraint else set()

        return {
            "table": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "primary_key": col["name"] in pk_columns,
                    "default": str(col["default"]) if col.get("default") is not None else None,
                }
                for col in columns
            ],
        }
