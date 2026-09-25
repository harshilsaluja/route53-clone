"""Phase 5 tests for authenticated logical DNS record sets."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func
from sqlmodel import Session as DatabaseSession, select

from app.models import (
    DNSRecordSet, DNSRecordType, DNSRecordValue, HostedZone, HostedZoneType, User,
)

ZONES = "/api/v1/hosted-zones"


@pytest.fixture
def logged_in(client: TestClient, demo_user: UUID) -> Iterator[TestClient]:
    response = client.post("/api/v1/auth/login", json={
        "email": "demo@route53clone.dev", "password": "Scaler@123",
    })
    assert response.status_code == 200
    yield client


@pytest.fixture
def zone(logged_in: TestClient) -> dict:
    response = logged_in.post(ZONES, json={"name": "example.com", "type": "PUBLIC"})
    assert response.status_code == 201
    return response.json()


def records(zone: dict) -> str:
    return f"{ZONES}/{zone['id']}/records"


def create(client: TestClient, zone: dict, **changes) -> dict:
    body = {"name": "www", "record_type": "A", "ttl": 300,
            "values": ["192.0.2.10"]}
    body.update(changes)
    response = client.post(records(zone), json=body)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("method,suffix,body", [
    ("GET", "", None),
    ("POST", "", {"name": "www", "record_type": "A", "ttl": 300,
                   "values": ["192.0.2.1"]}),
    ("GET", f"/{uuid4()}", None),
    ("PATCH", f"/{uuid4()}", {"ttl": 60}),
    ("DELETE", f"/{uuid4()}", None),
])
def test_every_operation_requires_auth(
    client: TestClient, method: str, suffix: str, body,
) -> None:
    response = client.request(
        method, f"{ZONES}/{uuid4()}/records{suffix}", json=body,
    )
    assert response.status_code == 401


@pytest.mark.parametrize("record_type,values,canonical", [
    ("A", ["192.0.2.10", "198.51.100.2"], ["192.0.2.10", "198.51.100.2"]),
    ("AAAA", ["2001:0db8:0:0:0:0:0:1"], ["2001:db8::1"]),
    ("CNAME", ["Target.EXAMPLE.net."], ["target.example.net"]),
    ("TXT", ['  Keep Case "and quotes" \\  '], ['  Keep Case "and quotes" \\  ']),
    ("MX", ["010   MAIL.example.net."], ["10 mail.example.net"]),
    ("NS", ["NS1.EXAMPLE.net."], ["ns1.example.net"]),
    ("PTR", ["Host.EXAMPLE.net."], ["host.example.net"]),
    ("SRV", ["010 005 0443 Service.EXAMPLE.net."],
     ["10 5 443 service.example.net"]),
    ("CAA", ['000 ISSUE "LetsEncrypt.org"'], ['0 issue "LetsEncrypt.org"']),
])
def test_all_types_validate_and_canonicalize(
    logged_in: TestClient, zone: dict, record_type: str,
    values: list[str], canonical: list[str],
) -> None:
    name = "alias" if record_type == "CNAME" else record_type.lower()
    item = create(
        logged_in, zone, name=name, record_type=record_type, values=values,
    )
    assert item["values"] == canonical
    assert item["fqdn"] == f"{name}.example.com"


@pytest.mark.parametrize("record_type,values", [
    ("A", ["999.1.1.1"]), ("A", ["2001:db8::1"]),
    ("AAAA", ["192.0.2.1"]), ("AAAA", ["2001:::1"]),
    ("CNAME", ["bad target"]), ("CNAME", ["a.example", "b.example"]),
    ("MX", ["65536 mail.example"]), ("MX", ["10 192.0.2.1"]),
    ("NS", ["bad_target.example"]), ("PTR", ["https://example.com"]),
    ("SRV", ["1 2 65536 target.example"]), ("SRV", ["1 2 3 bad target"]),
    ("CAA", ['256 issue "ca.example"']), ("CAA", ['0 unknown "ca.example"']),
    ("CAA", ['0 issue ""']),
])
def test_invalid_type_values_are_atomic(
    logged_in: TestClient, zone: dict, record_type: str, values: list[str],
) -> None:
    response = logged_in.post(records(zone), json={
        "name": "bad", "record_type": record_type, "ttl": 300, "values": values,
    })
    assert response.status_code == 422
    assert logged_in.get(records(zone)).json()["pagination"]["total"] == 0


def test_apex_relative_and_wildcard_names(logged_in: TestClient, zone: dict) -> None:
    apex = create(
        logged_in, zone, name="@", record_type="MX",
        values=["10 mail.example.net"],
    )
    assert (apex["name"], apex["fqdn"]) == ("", "example.com")
    for invalid in ("example.com", "www.example.com", "www.", "bad..name", "a\\b"):
        response = logged_in.post(records(zone), json={
            "name": invalid, "record_type": "A", "ttl": 60,
            "values": ["192.0.2.2"],
        })
        assert response.status_code == 422
    wildcard = create(logged_in, zone, name="*.sub")
    assert wildcard["fqdn"] == "*.sub.example.com"


def test_duplicates_and_cname_conflicts_both_directions(
    logged_in: TestClient, zone: dict,
) -> None:
    create(logged_in, zone, name="one")
    duplicate = logged_in.post(records(zone), json={
        "name": "one", "record_type": "A", "ttl": 60,
        "values": ["192.0.2.2"],
    })
    assert (duplicate.status_code, duplicate.json()["error"]["code"]) == (
        409, "DNS_RECORD_ALREADY_EXISTS",
    )
    conflict = logged_in.post(records(zone), json={
        "name": "one", "record_type": "CNAME", "ttl": 60,
        "values": ["target.example"],
    })
    assert (conflict.status_code, conflict.json()["error"]["code"]) == (
        409, "DNS_RECORD_CONFLICT",
    )
    create(
        logged_in, zone, name="two", record_type="CNAME",
        values=["target.example"],
    )
    reverse = logged_in.post(records(zone), json={
        "name": "two", "record_type": "TXT", "ttl": 60, "values": ["text"],
    })
    assert (reverse.status_code, reverse.json()["error"]["code"]) == (
        409, "DNS_RECORD_CONFLICT",
    )


def test_duplicate_canonical_values_and_apex_cname_rejected(
    logged_in: TestClient, zone: dict,
) -> None:
    duplicate = logged_in.post(records(zone), json={
        "name": "v6", "record_type": "AAAA", "ttl": 60,
        "values": ["2001:db8::1", "2001:0db8:0:0:0:0:0:1"],
    })
    assert duplicate.status_code == 422
    apex = logged_in.post(records(zone), json={
        "name": "", "record_type": "CNAME", "ttl": 60,
        "values": ["target.example"],
    })
    assert apex.status_code == 422


def test_all_supported_caa_tags(logged_in: TestClient, zone: dict) -> None:
    for tag in ("issue", "issuewild", "iodef"):
        item = create(
            logged_in, zone, name=tag, record_type="CAA",
            values=[f'0 {tag} "Value-{tag}"'],
        )
        assert item["values"] == [f'0 {tag} "Value-{tag}"']


def test_list_search_filter_pagination_and_sort(
    logged_in: TestClient, zone: dict,
) -> None:
    create(logged_in, zone, name="z", ttl=100,
           values=["192.0.2.11", "192.0.2.12"])
    create(logged_in, zone, name="a", record_type="TXT", ttl=200,
           values=["match first", "match second"])
    create(logged_in, zone, name="m", record_type="MX", ttl=300,
           values=["10 mail.example.net"])
    match = logged_in.get(records(zone), params={"search": "match"}).json()
    assert match["pagination"]["total"] == 1 and len(match["items"]) == 1
    assert logged_in.get(
        records(zone), params={"search": "a.example.com"},
    ).json()["pagination"]["total"] == 1
    assert logged_in.get(
        records(zone), params={"search": "mail.example"},
    ).json()["pagination"]["total"] == 1
    assert logged_in.get(
        records(zone), params={"record_type": "A"},
    ).json()["pagination"]["total"] == 1
    page = logged_in.get(records(zone), params={
        "page": 2, "page_size": 1, "sort_by": "ttl", "sort_order": "desc",
    }).json()
    assert page["pagination"] == {
        "page": 2, "page_size": 1, "total": 3, "pages": 3,
    }
    assert page["items"][0]["ttl"] == 200
    assert logged_in.get(records(zone), params={"page": 99}).json()["items"] == []


def test_detail_update_replaces_values_and_preserves_failed_state(
    logged_in: TestClient, zone: dict,
) -> None:
    item = create(logged_in, zone, values=["192.0.2.1", "192.0.2.2"])
    path = f"{records(zone)}/{item['id']}"
    assert logged_in.get(path).json()["values"] == ["192.0.2.1", "192.0.2.2"]
    no_op = logged_in.patch(path, json={"ttl": 300}).json()
    assert no_op["updated_at"] == item["updated_at"]
    changed = logged_in.patch(
        path, json={"ttl": 60, "values": ["192.0.2.9"]},
    )
    assert changed.status_code == 200
    assert changed.json()["values"] == ["192.0.2.9"]
    assert changed.json()["updated_at"] > item["updated_at"]
    assert logged_in.patch(path, json={"record_type": "AAAA"}).status_code == 422
    assert logged_in.get(path).json() == changed.json()
    converted = logged_in.patch(path, json={
        "record_type": "AAAA", "values": ["2001:0db8::9"],
    })
    assert converted.status_code == 200
    assert converted.json()["values"] == ["2001:db8::9"]


def test_update_rechecks_uniqueness_and_cname_conflict(
    logged_in: TestClient, zone: dict,
) -> None:
    create(logged_in, zone, name="first")
    second = create(logged_in, zone, name="second")
    path = f"{records(zone)}/{second['id']}"
    assert logged_in.patch(path, json={"name": "first"}).status_code == 409
    conflict = logged_in.patch(path, json={
        "name": "first", "record_type": "CNAME",
        "values": ["target.example"],
    })
    assert (conflict.status_code, conflict.json()["error"]["code"]) == (
        409, "DNS_RECORD_CONFLICT",
    )


def test_cross_zone_and_other_owner_are_hidden(
    logged_in: TestClient, zone: dict, db_engine,
) -> None:
    item = create(logged_in, zone)
    other_zone = logged_in.post(
        ZONES, json={"name": "other.example", "type": "PRIVATE"},
    ).json()
    assert logged_in.get(
        f"{records(other_zone)}/{item['id']}",
    ).status_code == 404
    with DatabaseSession(db_engine) as db:
        owner = User(
            email="foreign@example.com", password_hash="test-only",
            display_name="Foreign User",
        )
        foreign = HostedZone(
            user=owner, name="foreign.example", type=HostedZoneType.PUBLIC,
        )
        foreign_record = DNSRecordSet(
            hosted_zone=foreign, name="www",
            record_type=DNSRecordType.A, ttl=60,
        )
        foreign_record.values = [
            DNSRecordValue(position=0, value="192.0.2.20"),
        ]
        db.add(foreign_record)
        db.commit()
        foreign_id = foreign.id
        foreign_record_id = foreign_record.id
    base = f"{ZONES}/{foreign_id}/records"
    assert logged_in.get(base).status_code == 404
    assert logged_in.post(base, json={
        "name": "x", "record_type": "A", "ttl": 60,
        "values": ["192.0.2.1"],
    }).status_code == 404
    hidden = f"{base}/{foreign_record_id}"
    assert logged_in.get(hidden).status_code == 404
    assert logged_in.patch(hidden, json={"ttl": 120}).status_code == 404
    assert logged_in.delete(hidden).status_code == 404


def test_delete_cascades_values_and_updates_zone_counts(
    logged_in: TestClient, zone: dict, db_engine,
) -> None:
    first = create(
        logged_in, zone, name="one",
        values=["192.0.2.1", "192.0.2.2"],
    )
    second = create(
        logged_in, zone, name="two", record_type="TXT", values=["x"],
    )
    assert logged_in.get(f"{ZONES}/{zone['id']}").json()["record_count"] == 2
    assert logged_in.get(ZONES).json()["items"][0]["record_count"] == 2
    assert logged_in.delete(f"{records(zone)}/{first['id']}").status_code == 204
    assert logged_in.get(f"{records(zone)}/{first['id']}").status_code == 404
    assert logged_in.get(f"{ZONES}/{zone['id']}").json()["record_count"] == 1
    with DatabaseSession(db_engine) as db:
        count = db.exec(
            select(func.count()).select_from(DNSRecordValue).where(
                DNSRecordValue.record_set_id == UUID(first["id"]),
            )
        ).one()
        assert count == 0
        assert db.get(DNSRecordSet, UUID(second["id"])) is not None


def test_values_use_batched_eager_loading(
    logged_in: TestClient, zone: dict, db_engine,
) -> None:
    create(logged_in, zone, name="one")
    create(logged_in, zone, name="two")
    queries: list[str] = []

    def count_selects(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(db_engine, "before_cursor_execute", count_selects)
    try:
        assert logged_in.get(records(zone)).status_code == 200
        assert len(queries) <= 6
    finally:
        event.remove(db_engine, "before_cursor_execute", count_selects)


def test_openapi_declares_five_nested_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    collection = f"{ZONES}/{{zone_id}}/records"
    detail = collection + "/{record_id}"
    assert set(schema["paths"][collection]) == {"get", "post"}
    assert set(schema["paths"][detail]) == {"get", "patch", "delete"}
    query = {
        parameter["name"]
        for parameter in schema["paths"][collection]["get"]["parameters"]
    }
    assert query == {
        "zone_id", "search", "record_type", "page", "page_size",
        "sort_by", "sort_order",
    }
    assert set(schema["components"]["schemas"]["DNSRecordType"]["enum"]) == {
        "A", "AAAA", "CNAME", "TXT", "MX", "NS", "PTR", "SRV", "CAA",
    }


@pytest.mark.parametrize("body", [
    {}, {"ttl": None}, {"values": []}, {"routing_policy": "WEIGHTED"},
    {"unknown": "x"}, {"ttl": 0},
])
def test_invalid_patch_shapes(
    logged_in: TestClient, zone: dict, body: dict,
) -> None:
    item = create(logged_in, zone)
    response = logged_in.patch(
        f"{records(zone)}/{item['id']}", json=body,
    )
    assert response.status_code == 422
