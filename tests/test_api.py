"""Unit tests for database schema and API integration."""

import sqlite3

from fraud_detection.config import PROJECT_ROOT


def test_database_schema_sql_executes_cleanly() -> None:
    """Verify that `database/schema.sql` executes without syntax errors in SQLite."""
    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    with sqlite3.connect(":memory:") as conn:
        conn.executescript(schema_sql)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = [row[0] for row in cursor.fetchall()]

    assert "transactions" in tables
    assert "fraud_predictions" in tables
