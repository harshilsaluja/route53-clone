from pathlib import Path

from alembic import command
from sqlalchemy import Engine, inspect, text

from app.config import Settings
from app.database import create_sqlite_engine
from conftest import migration_config

TABLES = {"users", "sessions", "hosted_zones", "dns_record_sets", "dns_record_values"}


def test_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{(tmp_path / 'migration.db').as_posix()}")
    try:
        with engine.begin() as connection:
            assert inspect(connection).get_table_names() == []
            config = migration_config(connection)
            command.upgrade(config, "head")
            assert set(inspect(connection).get_table_names()) == TABLES | {"alembic_version"}
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
            command.check(config)
            command.downgrade(config, "base")
            assert set(inspect(connection).get_table_names()) == {"alembic_version"}
            assert connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0
            command.upgrade(config, "head")
            assert set(inspect(connection).get_table_names()) == TABLES | {"alembic_version"}
    finally:
        engine.dispose()


def test_foreign_keys_on_each_new_connection(db_engine: Engine) -> None:
    # Hold two connections at once so the pool must open another physical connection.
    with db_engine.connect() as first, db_engine.connect() as second:
        assert first.scalar(text("PRAGMA foreign_keys")) == 1
        assert second.scalar(text("PRAGMA foreign_keys")) == 1
    db_engine.dispose()
    with db_engine.connect() as reopened:
        assert reopened.scalar(text("PRAGMA foreign_keys")) == 1


def test_schema_primary_keys_foreign_keys_and_indexes(db_engine: Engine) -> None:
    schema = inspect(db_engine)
    for table in TABLES:
        assert schema.get_pk_constraint(table)["constrained_columns"] == ["id"]
        assert all(column["nullable"] is False for column in schema.get_columns(table)
                   if column["name"] != "comment")
    expected_parents = {
        "sessions": ("user_id", "users"),
        "hosted_zones": ("user_id", "users"),
        "dns_record_sets": ("hosted_zone_id", "hosted_zones"),
        "dns_record_values": ("record_set_id", "dns_record_sets"),
    }
    for table, (column, parent) in expected_parents.items():
        [foreign_key] = schema.get_foreign_keys(table)
        assert foreign_key["constrained_columns"] == [column]
        assert foreign_key["referred_table"] == parent
        assert foreign_key["options"]["ondelete"] == "CASCADE"
    assert schema.get_indexes("users")[0]["unique"] == 1
    assert {i["name"] for i in schema.get_indexes("sessions")} == {
        "ix_sessions_user_id", "ix_sessions_token_hash", "ix_sessions_expires_at",
    }
    assert schema.get_indexes("hosted_zones")[0]["column_names"] == ["user_id", "type"]
    assert schema.get_indexes("dns_record_sets")[0]["column_names"] == [
        "hosted_zone_id", "record_type",
    ]


def test_test_database_is_not_development_database(db_engine: Engine) -> None:
    from app.database import resolve_database_url

    configured = resolve_database_url(Settings().database_url)
    assert db_engine.url.database != configured.database
