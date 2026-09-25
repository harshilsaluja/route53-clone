"""Hosted Zone API tests against migrated, isolated SQLite databases."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session as DatabaseSession, select

from app.models import DNSRecordSet, DNSRecordType, DNSRecordValue, HostedZone, HostedZoneType, User
from app.schemas.hosted_zone import HostedZoneCreate, HostedZoneUpdate
from app.security import hash_password
from app.seed import DEMO_EMAIL, DEMO_PASSWORD
from app.services import hosted_zone_service

ZONES = "/api/v1/hosted-zones"


@pytest.fixture
def logged_in(client: TestClient, demo_user: UUID) -> TestClient:
    result = client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert result.status_code == 200
    return client


def create(client: TestClient, name: str = "example.com", **fields):
    return client.post(ZONES, json={"name": name, "type": "PUBLIC", **fields})


@pytest.fixture
def zone(logged_in: TestClient) -> dict:
    result = create(logged_in, comment="Original comment")
    assert result.status_code == 201
    return result.json()


@pytest.fixture
def catalog(db_engine: Engine, demo_user: UUID) -> list[HostedZone]:
    with DatabaseSession(db_engine, expire_on_commit=False) as db:
        rows = []
        for index, (name, kind, comment) in enumerate([
            ("alpha.example", "PUBLIC", "Production service"),
            ("beta.example", "PRIVATE", None),
            ("zeta.example", "PUBLIC", "Private word in public comment"),
            ("internal.example", "PRIVATE", "production service"),
            ("gamma.example", "PUBLIC", "100%_literal"),
        ]):
            row = HostedZone(user_id=demo_user, name=name, type=HostedZoneType(kind),
                             comment=comment, created_at=datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=index))
            db.add(row)
            rows.append(row)
        db.commit()
        return rows


def attach_records(db_engine: Engine, zone_id: str) -> tuple[UUID, UUID]:
    with DatabaseSession(db_engine) as db:
        address = DNSRecordSet(hosted_zone_id=UUID(zone_id), name="www",
                               record_type=DNSRecordType.A, ttl=300)
        address.values = [DNSRecordValue(position=i, value=f"192.0.2.{i + 1}") for i in range(3)]
        alias = DNSRecordSet(hosted_zone_id=UUID(zone_id), name="service",
                             record_type=DNSRecordType.CNAME, ttl=300)
        alias.values = [DNSRecordValue(position=0, value="target.external.com")]
        db.add_all([address, alias])
        db.commit()
        return address.id, alias.id


@pytest.mark.parametrize("method,path,body", [
    ("GET", ZONES, None), ("POST", ZONES, {"name": "example.com", "type": "PUBLIC"}),
    ("GET", f"{ZONES}/{uuid4()}", None),
    ("PATCH", f"{ZONES}/{uuid4()}", {"comment": "x"}),
    ("DELETE", f"{ZONES}/{uuid4()}", None),
])
def test_authentication_required(client: TestClient, method: str, path: str, body: dict | None) -> None:
    response = client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("kind", ["PUBLIC", "PRIVATE"])
def test_create_normalized_and_persisted(
    logged_in: TestClient, demo_user: UUID, db_engine: Engine, kind: str
) -> None:
    response = create(logged_in, "Example.COM.", type=kind, comment="Production domain")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "name", "type", "comment", "record_count", "created_at", "updated_at"}
    assert UUID(body["id"])
    assert body["name"] == "example.com" and body["type"] == kind
    assert body["comment"] == "Production domain" and body["record_count"] == 0
    assert datetime.fromisoformat(body["created_at"]).tzinfo == UTC
    assert datetime.fromisoformat(body["updated_at"]).tzinfo == UTC
    assert response.headers["cache-control"] == "no-store"
    with DatabaseSession(db_engine) as db:
        stored = db.get(HostedZone, UUID(body["id"]))
        assert stored is not None
        assert stored.user_id == demo_user and stored.name == "example.com"


@pytest.mark.parametrize("name", [
    "", ".", "example..com", "-example.com", "example-.com", "ex ample.com",
    "example.com/path", "https://example.com", "_service.example", "*.example.com",
    "bücher.example", "example.com..", "a" * 64 + ".com",
    ".".join(["a" * 63] * 4),
])
def test_invalid_names(logged_in: TestClient, name: str) -> None:
    response = create(logged_in, name)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("name", [
    "api.example.com", "example.co.in", "xn--bcher-kva.example",
    "a" * 63 + ".example", ".".join(["a" * 63] * 3 + ["a" * 61]),
])
def test_valid_domain_shapes_and_limits(logged_in: TestClient, name: str) -> None:
    response = create(logged_in, name)
    assert response.status_code == 201
    assert response.json()["name"] == name


@pytest.mark.parametrize("fields", [
    {"type": "OTHER"}, {"type": None}, {"user_id": str(uuid4())},
    {"extra": "value"}, {"name": None}, {"comment": "x" * 1025},
])
def test_strict_create_schema(logged_in: TestClient, fields: dict) -> None:
    assert create(logged_in, **fields).status_code == 422


def test_duplicate_rules(logged_in: TestClient) -> None:
    first = create(logged_in)
    assert first.status_code == 201
    duplicate = create(logged_in, "EXAMPLE.COM.")
    assert duplicate.status_code == 409
    assert duplicate.json() == {"error": {
        "code": "HOSTED_ZONE_ALREADY_EXISTS",
        "message": "A hosted zone with this name and type already exists.",
    }}
    assert create(logged_in, type="PRIVATE").status_code == 201
    assert logged_in.get(ZONES).json()["pagination"]["total"] == 2


def test_user_isolation(
    logged_in: TestClient, zone: dict, db_engine: Engine
) -> None:
    owner_cookie = logged_in.cookies.get("route53_session")
    with DatabaseSession(db_engine) as db:
        other = User(email="other@example.com", password_hash=hash_password("other-password"),
                     display_name="Other")
        db.add(other)
        db.commit()
    response = logged_in.post("/api/v1/auth/login", json={
        "email": "other@example.com", "password": "other-password",
    })
    assert response.status_code == 200
    path = f"{ZONES}/{zone['id']}"
    assert logged_in.get(ZONES).json()["items"] == []
    assert logged_in.get(ZONES, params={"search": "example"}).json()["items"] == []
    for response in (
        logged_in.get(path), logged_in.patch(path, json={"name": "stolen.example"}),
        logged_in.delete(path),
    ):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "HOSTED_ZONE_NOT_FOUND"
    own = create(logged_in)
    assert own.status_code == 201 and own.json()["id"] != zone["id"]
    listed = logged_in.get(ZONES).json()
    assert listed["pagination"]["total"] == 1
    assert [item["id"] for item in listed["items"]] == [own.json()["id"]]
    logged_in.cookies.clear()
    logged_in.cookies.set("route53_session", owner_cookie)
    assert logged_in.get(path).json()["name"] == "example.com"


def test_empty_listing(logged_in: TestClient) -> None:
    response = logged_in.get(ZONES)
    assert response.status_code == 200
    assert response.json() == {
        "items": [], "pagination": {"page": 1, "page_size": 20, "total": 0, "pages": 0},
    }


@pytest.mark.parametrize("params,names", [
    ({"search": "ALPHA"}, ["alpha.example"]),
    ({"search": " production "}, ["alpha.example", "internal.example"]),
    ({"search": "   "}, ["alpha.example", "beta.example", "gamma.example", "internal.example", "zeta.example"]),
    ({"type": "PUBLIC"}, ["alpha.example", "gamma.example", "zeta.example"]),
    ({"type": "PRIVATE"}, ["beta.example", "internal.example"]),
    ({"search": "production", "type": "PRIVATE"}, ["internal.example"]),
    ({"search": "%_"}, ["gamma.example"]),
    ({"search": "no-match"}, []),
    ({"search": "' OR 1=1 --"}, []),
])
def test_search_and_type_filters(
    logged_in: TestClient, catalog: list[HostedZone], params: dict, names: list[str]
) -> None:
    response = logged_in.get(ZONES, params=params)
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["items"]] == names
    assert body["pagination"]["total"] == len(names)


def test_pagination(logged_in: TestClient, catalog: list[HostedZone]) -> None:
    for page, names in [
        (1, ["alpha.example", "beta.example"]), (2, ["gamma.example", "internal.example"]),
        (3, ["zeta.example"]), (4, []), (10**30, []),
    ]:
        response = logged_in.get(ZONES, params={"page": page, "page_size": 2})
        assert response.status_code == 200
        body = response.json()
        assert [item["name"] for item in body["items"]] == names
        assert body["pagination"] == {"page": page, "page_size": 2, "total": 5, "pages": 3}
    filtered = logged_in.get(ZONES, params={"type": "PUBLIC", "page_size": 2, "page": 2}).json()
    assert filtered["pagination"]["total"] == 3 and filtered["pagination"]["pages"] == 2
    assert [item["name"] for item in filtered["items"]] == ["zeta.example"]


@pytest.mark.parametrize("params", [
    {"page": 0}, {"page": -1}, {"page": "bad"}, {"page_size": 0},
    {"page_size": -1}, {"page_size": 101}, {"page_size": "1.5"},
    {"type": "OTHER"}, {"sort_by": "comment"}, {"sort_by": "name; DROP TABLE users"},
    {"sort_order": "sideways"}, {"user_id": str(uuid4())}, {"unknown": "x"},
])
def test_query_validation(logged_in: TestClient, params: dict) -> None:
    response = logged_in.get(ZONES, params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("field,direction", [
    ("name", "asc"), ("name", "desc"), ("created_at", "asc"),
    ("created_at", "desc"), ("type", "asc"), ("type", "desc"),
])
def test_sorting(logged_in: TestClient, catalog: list[HostedZone], field: str, direction: str) -> None:
    response = logged_in.get(ZONES, params={"sort_by": field, "sort_order": direction})
    assert response.status_code == 200
    items = response.json()["items"]
    values = [item[field] for item in items]
    assert values == sorted(values, reverse=direction == "desc")
    for value in set(values):
        matching = [item["id"] for item in items if item[field] == value]
        assert matching == sorted(matching)


def test_stable_tie_breaker_across_pages(logged_in: TestClient, catalog: list[HostedZone]) -> None:
    expected = sorted(row.id for row in catalog if row.type == HostedZoneType.PUBLIC)
    actual = [
        logged_in.get(ZONES, params={"type": "PUBLIC", "sort_by": "type", "page_size": 1, "page": page})
        .json()["items"][0]["id"]
        for page in range(1, 4)
    ]
    assert actual == [str(identifier) for identifier in expected]


def test_owner_retrieves_zone(logged_in: TestClient, zone: dict) -> None:
    response = logged_in.get(f"{ZONES}/{zone['id']}")
    assert response.status_code == 200 and response.json() == zone


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_unknown_zone(logged_in: TestClient, method: str) -> None:
    response = logged_in.request(method, f"{ZONES}/{uuid4()}",
                                  json={"comment": "x"} if method == "PATCH" else None)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HOSTED_ZONE_NOT_FOUND"


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_invalid_uuid(logged_in: TestClient, method: str) -> None:
    response = logged_in.request(method, f"{ZONES}/not-a-uuid",
                                  json={"comment": "x"} if method == "PATCH" else None)
    assert response.status_code == 422


def test_partial_comment_update_and_clear(logged_in: TestClient, zone: dict) -> None:
    path = f"{ZONES}/{zone['id']}"
    response = logged_in.patch(path, json={"comment": "Updated comment"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["comment"] == "Updated comment"
    for field in ("id", "name", "type", "created_at", "record_count"):
        assert updated[field] == zone[field]
    assert datetime.fromisoformat(updated["updated_at"]) > datetime.fromisoformat(zone["updated_at"])
    assert logged_in.patch(path, json={"comment": None}).json()["comment"] is None


def test_rename_and_type_changes(logged_in: TestClient, zone: dict) -> None:
    path = f"{ZONES}/{zone['id']}"
    renamed = logged_in.patch(path, json={"name": "EXAMPLE.DEV."})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "example.dev"
    assert renamed.json()["comment"] == zone["comment"]
    for kind in ("PRIVATE", "PUBLIC"):
        updated = logged_in.patch(path, json={"type": kind})
        assert updated.status_code == 200 and updated.json()["type"] == kind


@pytest.mark.parametrize("payload", [
    {}, {"name": None}, {"type": None}, {"name": "-invalid.example"},
    {"type": "OTHER"}, {"user_id": str(uuid4())}, {"record_count": 10},
    {"comment": "x" * 1025},
])
def test_invalid_patch(logged_in: TestClient, zone: dict, payload: dict) -> None:
    response = logged_in.patch(f"{ZONES}/{zone['id']}", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert logged_in.get(f"{ZONES}/{zone['id']}").json() == zone


@pytest.mark.parametrize("conflict", ["rename", "type"])
def test_update_conflicts_are_atomic(logged_in: TestClient, zone: dict, conflict: str) -> None:
    if conflict == "rename":
        assert create(logged_in, "taken.example").status_code == 201
        payload = {"name": "TAKEN.EXAMPLE.", "comment": "Should roll back"}
    else:
        assert create(logged_in, type="PRIVATE").status_code == 201
        payload = {"type": "PRIVATE", "comment": "Should roll back"}
    response = logged_in.patch(f"{ZONES}/{zone['id']}", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "HOSTED_ZONE_ALREADY_EXISTS"
    assert logged_in.get(f"{ZONES}/{zone['id']}").json() == zone


def test_delete_cascades_records(
    logged_in: TestClient, zone: dict, db_engine: Engine
) -> None:
    attach_records(db_engine, zone["id"])
    response = logged_in.delete(f"{ZONES}/{zone['id']}")
    assert response.status_code == 204 and response.content == b""
    assert logged_in.get(f"{ZONES}/{zone['id']}").status_code == 404
    with DatabaseSession(db_engine) as db:
        assert db.get(HostedZone, UUID(zone["id"])) is None
        assert db.exec(select(DNSRecordSet)).all() == []
        assert db.exec(select(DNSRecordValue)).all() == []


def test_counts_are_record_sets_not_values(
    logged_in: TestClient, zone: dict, db_engine: Engine
) -> None:
    attach_records(db_engine, zone["id"])
    detail = logged_in.get(f"{ZONES}/{zone['id']}").json()
    listing = logged_in.get(ZONES).json()
    assert detail["record_count"] == 2
    assert listing["items"][0]["record_count"] == 2
    assert listing["pagination"]["total"] == 1
    updated = logged_in.patch(f"{ZONES}/{zone['id']}", json={"comment": "Count unchanged"})
    assert updated.json()["record_count"] == 2
    with DatabaseSession(db_engine) as db:
        assert len(db.exec(select(DNSRecordValue)).all()) == 4


def test_rename_preserves_record_rows_and_target_values(
    logged_in: TestClient, zone: dict, db_engine: Engine
) -> None:
    ids = attach_records(db_engine, zone["id"])
    with DatabaseSession(db_engine) as db:
        before = [value.model_dump() for value in db.exec(
            select(DNSRecordValue).order_by(DNSRecordValue.id)).all()]
    updated = logged_in.patch(f"{ZONES}/{zone['id']}", json={"name": "example.dev"})
    assert updated.status_code == 200
    with DatabaseSession(db_engine) as db:
        records = [db.get(DNSRecordSet, identifier) for identifier in ids]
        assert [record.name for record in records] == ["www", "service"]
        assert [record.name + "." + record.hosted_zone.name for record in records] == [
            "www.example.dev", "service.example.dev",
        ]
        after = [value.model_dump() for value in db.exec(
            select(DNSRecordValue).order_by(DNSRecordValue.id)).all()]
        assert after == before


def test_list_query_count_does_not_grow_with_page_size(
    logged_in: TestClient, catalog: list[HostedZone], db_engine: Engine
) -> None:
    queries: list[str] = []

    def record_query(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(db_engine, "before_cursor_execute", record_query)
    try:
        assert logged_in.get(ZONES, params={"page_size": 1}).status_code == 200
        one_count = len(queries)
        queries.clear()
        assert len(logged_in.get(ZONES, params={"page_size": 20}).json()["items"]) == 5
        assert len(queries) == one_count
        assert len(queries) <= 4  # session + user + total + grouped page
    finally:
        event.remove(db_engine, "before_cursor_execute", record_query)


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_mutation_origin_protection(logged_in: TestClient, zone: dict, method: str) -> None:
    path = ZONES if method == "POST" else f"{ZONES}/{zone['id']}"
    body = {"name": "new.example", "type": "PUBLIC"} if method == "POST" else {"comment": "x"}
    response = logged_in.request(method, path, json=body,
                                  headers={"Origin": "https://unapproved.example"})
    assert response.status_code == 403
    assert logged_in.get(f"{ZONES}/{zone['id']}").json() == zone


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_cors_allows_new_methods(client: TestClient, method: str) -> None:
    response = client.options(f"{ZONES}/{uuid4()}", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert method in response.headers["access-control-allow-methods"]


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_write_failure_rolls_back(
    db_engine: Engine, demo_user: UUID, zone: dict, operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with DatabaseSession(db_engine) as db:
        def fail_commit():
            raise SQLAlchemyError("simulated commit failure")
        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(SQLAlchemyError):
            if operation == "create":
                hosted_zone_service.create_zone(db, demo_user, HostedZoneCreate(name="new.example", type="PUBLIC"))
            elif operation == "update":
                hosted_zone_service.update_zone(db, demo_user, UUID(zone["id"]), HostedZoneUpdate(comment="changed"))
            else:
                hosted_zone_service.delete_zone(db, demo_user, UUID(zone["id"]))
        assert not db.in_transaction()
    with DatabaseSession(db_engine) as db:
        rows = db.exec(select(HostedZone)).all()
        assert len(rows) == 1 and rows[0].comment == zone["comment"]


def test_openapi_declares_hosted_zone_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"][ZONES]) == {"get", "post"}
    assert set(schema["paths"][ZONES + "/{zone_id}"]) == {"get", "patch", "delete"}
    query_fields = {item["name"] for item in schema["paths"][ZONES]["get"]["parameters"]}
    assert query_fields == {"search", "type", "page", "page_size", "sort_by", "sort_order"}
    assert not any("/records" in path for path in schema["paths"])
