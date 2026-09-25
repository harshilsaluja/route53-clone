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

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import BACKEND_DIR, Settings
from app.database import create_sqlite_engine, get_session
from app.main import create_app
from app.seed import seed_demo_user
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


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        _env_file=None, allowed_frontend_origins=["http://localhost:3000"],
        session_cookie_name="route53_session", session_cookie_secure=False,
        session_cookie_samesite="lax", session_ttl_seconds=86400,
    )


@pytest.fixture
def auth_app(db_engine: Engine, auth_settings: Settings) -> FastAPI:
    application = create_app(auth_settings)

    def isolated_session() -> Generator[DatabaseSession, None, None]:
        with DatabaseSession(db_engine) as db:
            yield db

    application.dependency_overrides[get_session] = isolated_session
    return application


@pytest.fixture
def client(auth_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(auth_app, base_url="http://localhost:8000") as test_client:
        yield test_client


@pytest.fixture
def demo_user(db_engine: Engine) -> UUID:
    with DatabaseSession(db_engine) as db:
        user, _ = seed_demo_user(db)
        return user.id
