"""SQLite engines and request-scoped sessions; schema changes use Alembic."""

import sqlite3
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine, URL, make_url
from sqlmodel import Session, create_engine

from app.config import BACKEND_DIR, get_settings


def resolve_database_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    if url.drivername != "sqlite":
        raise ValueError("DATABASE_URL must use SQLite (sqlite:///...).")
    if url.database and url.database != ":memory:":
        database_path = Path(url.database)
        if not database_path.is_absolute():
            database_path = BACKEND_DIR / database_path
        url = url.set(database=str(database_path.resolve()))
    return url


def enable_foreign_keys(connection: sqlite3.Connection, _record: object) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_sqlite_engine(database_url: str | URL) -> Engine:
    """Share connection settings between the application, migrations, and tests."""
    url = resolve_database_url(str(database_url))
    db_engine = create_engine(
        url, connect_args={"check_same_thread": False, "timeout": 5}
    )
    event.listen(db_engine, "connect", enable_foreign_keys)
    return db_engine


engine = create_sqlite_engine(get_settings().database_url)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
