"""Use registered SQLModel metadata and the application's SQLite configuration."""

from alembic import context
from sqlalchemy import Connection
from sqlmodel import SQLModel
from sqlmodel.sql.sqltypes import AutoString

from app import models  # noqa: F401 - registers every table
from app.config import get_settings
from app.database import create_sqlite_engine, resolve_database_url
from app.models.common import UTCDateTime

config = context.config
target_metadata = SQLModel.metadata


def render_item(kind: str, obj: object, _context: object) -> str | bool:
    # Migrations freeze SQL storage types, not imports of mutable application types.
    if kind == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    if kind == "type" and isinstance(obj, AutoString):
        return "sa.String()"
    return False


def run_with_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=resolve_database_url(get_settings().database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        # Tests pass their isolated connection explicitly; never choose dev storage.
        run_with_connection(supplied_connection)
    else:
        migration_engine = create_sqlite_engine(get_settings().database_url)
        try:
            with migration_engine.connect() as connection:
                run_with_connection(connection)
        finally:
            migration_engine.dispose()
