from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlmodel import Session as DatabaseSession, select

from app.models import (
    DNSRecordSet, DNSRecordType, DNSRecordValue, HostedZone,
    HostedZoneType, Session, User,
)
from app.normalization import normalize_email, normalize_zone_name


def assert_rejected(engine: Engine, sql: str, parameters: dict[str, object]) -> None:
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(sql), parameters)


def test_user_email_unique(db_engine: Engine, graph: dict[str, UUID]) -> None:
    assert_rejected(db_engine,
        "INSERT INTO users (id,email,password_hash,display_name) VALUES (:id,:email,'x','x')",
        {"id": uuid4().hex, "email": "one@example.com"})


def test_session_token_hash_unique(db_engine: Engine, graph: dict[str, UUID]) -> None:
    assert_rejected(db_engine,
        "INSERT INTO sessions (id,user_id,token_hash,expires_at) "
        "VALUES (:id,:user,'test-token-hash-one','2030-01-01 00:00:00')",
        {"id": uuid4().hex, "user": graph["user_two"].hex})


def test_zone_unique_per_owner_name_type(db_engine: Engine, graph: dict[str, UUID]) -> None:
    assert_rejected(db_engine,
        "INSERT INTO hosted_zones (id,user_id,name,type) VALUES (:id,:user,'example.com','PUBLIC')",
        {"id": uuid4().hex, "user": graph["user_one"].hex})


def test_private_and_public_allowed(db_engine: Engine, graph: dict[str, UUID]) -> None:
    with DatabaseSession(db_engine) as db:
        db.add(HostedZone(user_id=graph["user_one"], name="example.com",
                          type=HostedZoneType.PRIVATE))
        db.commit()
        zones = db.exec(select(HostedZone).where(HostedZone.user_id == graph["user_one"])).all()
        assert {zone.type for zone in zones} == {HostedZoneType.PUBLIC, HostedZoneType.PRIVATE}


def test_different_owners_can_share_zone_name(db_engine: Engine, graph: dict[str, UUID]) -> None:
    with DatabaseSession(db_engine) as db:
        zones = db.exec(select(HostedZone)).all()
        assert len(zones) == 2
        assert {zone.user_id for zone in zones} == {graph["user_one"], graph["user_two"]}
        assert all(zone.name == "example.com" and zone.type == HostedZoneType.PUBLIC for zone in zones)


def test_record_set_unique(db_engine: Engine, graph: dict[str, UUID]) -> None:
    assert_rejected(db_engine,
        "INSERT INTO dns_record_sets (id,hosted_zone_id,name,record_type,ttl) "
        "VALUES (:id,:zone,'www','A',300)",
        {"id": uuid4().hex, "zone": graph["zone_one"].hex})


@pytest.mark.parametrize("record_type", list(DNSRecordType))
def test_supported_record_types_and_apex(
    db_engine: Engine, graph: dict[str, UUID], record_type: DNSRecordType
) -> None:
    with DatabaseSession(db_engine) as db:
        record = DNSRecordSet(hosted_zone_id=graph["zone_one"], name="",
                              record_type=record_type, ttl=300)
        db.add(record)
        db.commit()
        db.refresh(record)
        assert record.name == ""
        assert record.record_type == record_type
        assert record.routing_policy.value == "SIMPLE"


@pytest.mark.parametrize("ttl", [0, -1])
def test_ttl_must_be_positive(db_engine: Engine, graph: dict[str, UUID], ttl: int) -> None:
    assert_rejected(db_engine,
        "INSERT INTO dns_record_sets (id,hosted_zone_id,name,record_type,ttl) "
        "VALUES (:id,:zone,'invalid','A',:ttl)",
        {"id": uuid4().hex, "zone": graph["zone_one"].hex, "ttl": ttl})


@pytest.mark.parametrize("position", [-1, 0])
def test_value_position_nonnegative_and_unique(
    db_engine: Engine, graph: dict[str, UUID], position: int
) -> None:
    assert_rejected(db_engine,
        "INSERT INTO dns_record_values (id,record_set_id,position,value) "
        "VALUES (:id,:record,:position,'192.0.2.10')",
        {"id": uuid4().hex, "record": graph["record_one"].hex, "position": position})


def test_multiple_values_are_ordered(db_engine: Engine, graph: dict[str, UUID]) -> None:
    with DatabaseSession(db_engine) as db:
        record = db.get(DNSRecordSet, graph["record_one"])
        assert record is not None
        assert [value.position for value in record.values] == [0, 1, 2]
        assert [value.value for value in record.values] == [
            "13.20.30.40", "13.20.30.41", "13.20.30.42",
        ]
        assert len({value.id for value in record.values}) == 3


@pytest.mark.parametrize("table,id_key,remaining", [
    ("dns_record_sets", "record_one", [2, 2, 2, 1, 3]),
    ("hosted_zones", "zone_one", [2, 2, 1, 1, 3]),
    ("users", "user_one", [1, 1, 1, 1, 3]),
])
def test_raw_sql_delete_cascades(
    db_engine: Engine, graph: dict[str, UUID], table: str, id_key: str, remaining: list[int]
) -> None:
    # Fixed test table names only. Direct SQL proves database-level cascades.
    with db_engine.begin() as connection:
        connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": graph[id_key].hex})
        counts = [
            connection.scalar(text(f"SELECT count(*) FROM {name}"))
            for name in ("users", "sessions", "hosted_zones", "dns_record_sets", "dns_record_values")
        ]
        assert counts == remaining
        assert connection.scalar(text("SELECT count(*) FROM users WHERE id=:id"),
                                 {"id": graph["user_two"].hex}) == 1


def test_orm_delete_with_loaded_relationships(db_engine: Engine, graph: dict[str, UUID]) -> None:
    with DatabaseSession(db_engine) as db:
        user = db.get(User, graph["user_one"])
        assert user is not None
        assert len(user.sessions) == len(user.hosted_zones) == 1
        assert len(user.hosted_zones[0].records[0].values) == 3
        db.delete(user)
        db.commit()
    with DatabaseSession(db_engine) as db:
        assert db.get(User, graph["user_one"]) is None
        assert db.get(HostedZone, graph["zone_one"]) is None
        assert db.get(DNSRecordSet, graph["record_one"]) is None


@pytest.mark.parametrize("sql", [
    "INSERT INTO sessions (id,user_id,token_hash,expires_at) VALUES (:id,:parent,'orphan','2030-01-01')",
    "INSERT INTO hosted_zones (id,user_id,name,type) VALUES (:id,:parent,'example.com','PUBLIC')",
    "INSERT INTO dns_record_sets (id,hosted_zone_id,name,record_type,ttl) VALUES (:id,:parent,'','A',300)",
    "INSERT INTO dns_record_values (id,record_set_id,position,value) VALUES (:id,:parent,0,'x')",
])
def test_orphan_foreign_keys_rejected(db_engine: Engine, sql: str) -> None:
    assert_rejected(db_engine, sql, {"id": uuid4().hex, "parent": uuid4().hex})


@pytest.mark.parametrize("column,value", [
    ("record_type", "SOA"), ("record_type", "BOGUS"), ("routing_policy", "WEIGHTED"),
])
def test_record_enum_constraints(
    db_engine: Engine, graph: dict[str, UUID], column: str, value: str
) -> None:
    assert_rejected(db_engine, f"UPDATE dns_record_sets SET {column}=:value WHERE id=:id",
                    {"value": value, "id": graph["record_one"].hex})


def test_zone_enum_constraint(db_engine: Engine, graph: dict[str, UUID]) -> None:
    assert_rejected(db_engine, "UPDATE hosted_zones SET type='OTHER' WHERE id=:id",
                    {"id": graph["zone_one"].hex})


@pytest.mark.parametrize("name", ["Example.COM", "example.com.", " example.com", ""])
def test_zone_requires_explicit_normalization(
    db_engine: Engine, graph: dict[str, UUID], name: str
) -> None:
    assert_rejected(db_engine, "UPDATE hosted_zones SET name=:name WHERE id=:id",
                    {"name": name, "id": graph["zone_one"].hex})


def test_normalization_helpers_and_email_check(db_engine: Engine, graph: dict[str, UUID]) -> None:
    assert normalize_zone_name(" Example.COM. ") == "example.com"
    assert normalize_email(" Demo@Example.COM ") == "demo@example.com"
    assert_rejected(db_engine, "UPDATE users SET email='One@Example.com' WHERE id=:id",
                    {"id": graph["user_one"].hex})


def test_uuid_and_utc_round_trip_and_update(db_engine: Engine) -> None:
    old_time = datetime(2020, 1, 1, 12, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    with DatabaseSession(db_engine) as db:
        user = User(email="time@example.com", password_hash="test", display_name="Before",
                    created_at=old_time, updated_at=old_time)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert isinstance(user.id, UUID)
        assert user.created_at == old_time.astimezone(UTC)
        assert user.created_at.tzinfo == UTC
        assert user.updated_at.tzinfo == UTC
        user.display_name = "After"
        db.commit()
        db.refresh(user)
        assert user.updated_at > old_time
        assert user.updated_at.tzinfo == UTC
        assert user.created_at == old_time.astimezone(UTC)


def test_session_timestamps_are_aware(db_engine: Engine, graph: dict[str, UUID]) -> None:
    with DatabaseSession(db_engine) as db:
        session = db.get(Session, graph["session_one"])
        assert session is not None
        assert session.created_at.tzinfo == session.expires_at.tzinfo == UTC
        assert session.expires_at > session.created_at


def test_naive_timestamps_rejected(db_engine: Engine) -> None:
    with DatabaseSession(db_engine) as db:
        db.add(User(email="naive@example.com", password_hash="test", display_name="Test",
                    created_at=datetime(2020, 1, 1)))
        with pytest.raises(StatementError, match="timezone-aware"):
            db.commit()
        db.rollback()


def test_failed_transaction_does_not_leave_partial_record(db_engine: Engine, graph: dict[str, UUID]) -> None:
    record_id = uuid4()
    with DatabaseSession(db_engine) as db:
        record = DNSRecordSet(id=record_id, hosted_zone_id=graph["zone_one"],
                              name="rollback", record_type=DNSRecordType.A, ttl=300)
        record.values = [DNSRecordValue(position=0, value="192.0.2.1"),
                         DNSRecordValue(position=-1, value="192.0.2.2")]
        db.add(record)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    with DatabaseSession(db_engine) as db:
        assert db.get(DNSRecordSet, record_id) is None


def test_rename_preserves_relative_names_and_values(db_engine: Engine, graph: dict[str, UUID]) -> None:
    with DatabaseSession(db_engine) as db:
        zone = db.get(HostedZone, graph["zone_one"])
        assert zone is not None
        zone.name = normalize_zone_name("Changed.EXAMPLE.")
        db.commit()
    with DatabaseSession(db_engine) as db:
        record = db.get(DNSRecordSet, graph["record_one"])
        assert record is not None
        assert record.name == "www"
        assert record.hosted_zone.name == "changed.example"
        assert [v.value for v in record.values] == ["13.20.30.40", "13.20.30.41", "13.20.30.42"]
