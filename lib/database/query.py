from sqlalchemy import text
from sqlalchemy.orm import Session


def safe_query(session: Session, sql: str, **params) -> list[dict]:
    """
    Execute parameterized raw SQL and return rows as list of dicts.

    Usage (CORRECT — params are bound, never interpolated):
        safe_query(session, "SELECT * FROM orders WHERE user_id = :uid", uid=42)

    Never pass user input directly into the sql string.
    """
    result = session.execute(text(sql), params)
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]
