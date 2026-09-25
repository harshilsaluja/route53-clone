"""Every test gets a migrated SQLite file under pytest's temporary directory."""

from collections.abc import Generator
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine
from sqlmodel import Session as DatabaseSession

from app.config import BACKEND_DIR
from app.database import create_sqlite_engine
from app.models import (
    DNSRecordSet, DNSRecordType, DNSRecordValue, HostedZone,
    HostedZoneType, Session, User,
)
from app.models.common import utc_now


def migration_config(connection: Connection) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


@pytest.fixture
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    # Never use the application engine or its configured development database.
    engine = create_sqlite_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    with engine.begin() as connection:
        command.upgrade(migration_config(connection), "head")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def graph(db_engine: Engine) -> dict[str, UUID]:
    """Two independent owners, each with a complete persistent resource tree."""
    ids: dict[str, UUID] = {}
    with DatabaseSession(db_engine) as db:
        for suffix in ("one", "two"):
            user = User(
                email=f"{suffix}@example.com", password_hash="test-only-hash",
                display_name=suffix,
            )
            zone = HostedZone(
                user=user, name="example.com", type=HostedZoneType.PUBLIC
            )
            record = DNSRecordSet(
                hosted_zone=zone, name="www", record_type=DNSRecordType.A, ttl=300
            )
            # Deliberately insert out of order to exercise relationship ordering.
            record.values = [
                DNSRecordValue(position=position, value=f"13.20.30.{40 + position}")
                for position in (2, 0, 1)
            ]
            session = Session(
                user=user, token_hash=f"test-token-hash-{suffix}",
                expires_at=utc_now() + timedelta(days=1),
            )
            db.add_all([user, zone, record, session])
            db.flush()
            ids.update({
                f"user_{suffix}": user.id, f"zone_{suffix}": zone.id,
                f"record_{suffix}": record.id, f"session_{suffix}": session.id,
            })
        db.commit()
    return ids
