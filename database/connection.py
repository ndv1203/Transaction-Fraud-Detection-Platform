"""Database connection, engine creation, and DDL initialization for PostgreSQL 3-Tier architecture."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fraud_detection.config import PROJECT_ROOT, load_config
from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_SQL_PATH = PROJECT_ROOT / "database" / "schema.sql"


def load_schema_sql(schema_path: str | Path = SCHEMA_SQL_PATH) -> str:
    """Read the 3-tier PostgreSQL DDL script (`database/schema.sql`)."""
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Database DDL file not found: {path}")
    return path.read_text(encoding="utf-8")


class DatabaseManager:
    """Manages PostgreSQL / SQLAlchemy connections and 3-tier schema initialization."""

    def __init__(self, url: str | None = None, echo: bool | None = None) -> None:
        cfg = load_config()
        self.url = url or cfg.database.url
        self.echo = cfg.database.echo if echo is None else echo
        self._engine: Any = None
        self._session_factory: Any = None

    @property
    def engine(self) -> Any:
        """Lazily initialize a SQLAlchemy Engine when `sqlalchemy` is installed."""
        if self._engine is None:
            try:
                from sqlalchemy import create_engine
            except ImportError as exc:
                raise RuntimeError(
                    "SQLAlchemy is required to open a live database connection. "
                    "Install it via `uv add sqlalchemy psycopg[binary]`."
                ) from exc
            self._engine = create_engine(self.url, echo=self.echo, pool_pre_ping=True)
        return self._engine

    @contextmanager
    def session(self) -> Iterator[Any]:
        """Provide a transactional SQLAlchemy Session scope."""
        if self._session_factory is None:
            from sqlalchemy.orm import sessionmaker

            self._session_factory = sessionmaker(
                bind=self.engine, autoflush=False, autocommit=False
            )
        sess = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def init_schema(self, schema_path: str | Path = SCHEMA_SQL_PATH) -> None:
        """Execute `database/schema.sql` against the configured PostgreSQL database."""
        from sqlalchemy import text

        ddl = load_schema_sql(schema_path)
        with self.engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Initialized 3-tier PostgreSQL schema from %s.", schema_path)
