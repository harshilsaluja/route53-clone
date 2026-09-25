"""Owner-scoped DNS record sets with atomic ordered-value writes."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import case, delete, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.errors import APIError
from app.models import DNSRecordSet, DNSRecordType, DNSRecordValue, HostedZone
from app.models.common import utc_now
from app.schemas.common import PaginationMetadata
from app.schemas.dns_record import (
    DNSRecordCreate, DNSRecordListQuery, DNSRecordListResponse,
    DNSRecordResponse, DNSRecordUpdate,
)
from app.services.hosted_zone_service import get_owned_zone
from app.validation.dns_names import record_fqdn, validate_record_name
from app.validation.record_values import canonicalize_values


@contextmanager
def _write_transaction(db: Session) -> Iterator[None]:
    try:
        # sqlite3 legacy mode does not BEGIN on authentication SELECTs. Acquire
        # the writer lock BEFORE conflict reads, including CNAME coexistence.
        db.exec(text("BEGIN IMMEDIATE"))
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if (
            isinstance(exc.orig, sqlite3.IntegrityError)
            and getattr(exc.orig, "sqlite_errorcode", None) == sqlite3.SQLITE_CONSTRAINT_UNIQUE
            and str(exc.orig) == (
                "UNIQUE constraint failed: dns_record_sets.hosted_zone_id, "
                "dns_record_sets.name, dns_record_sets.record_type"
            )
        ):
            raise APIError(409, "DNS_RECORD_ALREADY_EXISTS",
                           "A record with this name and type already exists.") from None
        raise
    except Exception:
        db.rollback()
        raise


def _get_record(db: Session, zone_id: UUID, record_id: UUID) -> DNSRecordSet:
    record = db.exec(
        select(DNSRecordSet).where(
            DNSRecordSet.id == record_id, DNSRecordSet.hosted_zone_id == zone_id,
        ).options(selectinload(DNSRecordSet.values))
    ).first()
    if record is None:
        raise APIError(404, "DNS_RECORD_NOT_FOUND", "DNS record was not found.")
    return record


def _response(record: DNSRecordSet, zone: HostedZone) -> DNSRecordResponse:
    return DNSRecordResponse(
        **record.model_dump(), fqdn=record_fqdn(record.name, zone.name),
        values=[value.value for value in record.values],
    )


def _validate(
    payload: DNSRecordCreate, zone: HostedZone, *, supplied_name: bool = True,
) -> tuple[str, list[str]]:
    try:
        name = validate_record_name(payload.name, zone.name, supplied_name=supplied_name)
    except ValueError:
        raise APIError(422, "VALIDATION_ERROR", "Invalid relative record owner name.") from None
    try:
        if payload.record_type == DNSRecordType.CNAME and not name:
            raise ValueError("Apex CNAME is not supported.")
        values = canonicalize_values(payload.record_type, payload.values)
    except ValueError:
        # Do not echo values, which can include private TXT verification data.
        raise APIError(422, "INVALID_DNS_RECORD_VALUE",
                       "Values are invalid for the resulting DNS record.") from None
    return name, values


def _check_conflicts(
    db: Session, zone_id: UUID, name: str, record_type: DNSRecordType,
    record_id: UUID | None = None,
) -> None:
    conditions = [DNSRecordSet.hosted_zone_id == zone_id, DNSRecordSet.name == name]
    if record_id is not None:
        conditions.append(DNSRecordSet.id != record_id)
    types = db.exec(select(DNSRecordSet.record_type).where(*conditions)).all()
    if record_type in types:
        raise APIError(409, "DNS_RECORD_ALREADY_EXISTS",
                       "A record with this name and type already exists.")
    if types and (record_type == DNSRecordType.CNAME or DNSRecordType.CNAME in types):
        raise APIError(409, "DNS_RECORD_CONFLICT",
                       "CNAME cannot coexist with other records at this name.")


def create_record(
    db: Session, user_id: UUID, zone_id: UUID, payload: DNSRecordCreate,
) -> DNSRecordResponse:
    with _write_transaction(db):
        zone = get_owned_zone(db, user_id, zone_id)
        name, values = _validate(payload, zone)
        _check_conflicts(db, zone_id, name, payload.record_type)
        record = DNSRecordSet(
            hosted_zone_id=zone_id, **payload.model_dump(exclude={"name", "values"}), name=name,
        )
        record.values = [
            DNSRecordValue(position=position, value=value)
            for position, value in enumerate(values)
        ]
        db.add(record)
        db.flush()
        response = _response(record, zone)
    return response


def get_record(db: Session, user_id: UUID, zone_id: UUID, record_id: UUID) -> DNSRecordResponse:
    zone = get_owned_zone(db, user_id, zone_id)
    return _response(_get_record(db, zone_id, record_id), zone)


def list_records(
    db: Session, user_id: UUID, zone_id: UUID, query: DNSRecordListQuery,
) -> DNSRecordListResponse:
    zone = get_owned_zone(db, user_id, zone_id)
    conditions = [DNSRecordSet.hosted_zone_id == zone_id]
    search = query.search.strip()
    if search:
        fqdn = case(
            (DNSRecordSet.name == "", zone.name),
            else_=col(DNSRecordSet.name) + "." + zone.name,
        )
        conditions.append(or_(
            col(DNSRecordSet.name).icontains(search, autoescape=True),
            fqdn.icontains(search, autoescape=True),
            DNSRecordSet.values.any(col(DNSRecordValue.value).icontains(search, autoescape=True)),
        ))
    if query.record_type is not None:
        conditions.append(DNSRecordSet.record_type == query.record_type)
    total = db.exec(select(func.count()).select_from(DNSRecordSet).where(*conditions)).one()
    pagination = PaginationMetadata(
        page=query.page, page_size=query.page_size, total=total,
        pages=(total + query.page_size - 1) // query.page_size,
    )
    offset = (query.page - 1) * query.page_size
    if offset >= total:
        return DNSRecordListResponse(items=[], pagination=pagination)
    sort_column = {
        "name": DNSRecordSet.name, "record_type": DNSRecordSet.record_type,
        "ttl": DNSRecordSet.ttl, "created_at": DNSRecordSet.created_at,
    }[query.sort_by]
    primary_order = sort_column.asc() if query.sort_order == "asc" else sort_column.desc()
    records = db.exec(
        select(DNSRecordSet).where(*conditions).options(selectinload(DNSRecordSet.values))
        .order_by(primary_order, DNSRecordSet.id.asc()).offset(offset).limit(query.page_size)
    ).all()
    return DNSRecordListResponse(
        items=[_response(record, zone) for record in records], pagination=pagination,
    )


def update_record(
    db: Session, user_id: UUID, zone_id: UUID, record_id: UUID, payload: DNSRecordUpdate,
) -> DNSRecordResponse:
    with _write_transaction(db):
        zone = get_owned_zone(db, user_id, zone_id)
        record = _get_record(db, zone_id, record_id)
        old_values = [value.value for value in record.values]
        merged = {field: getattr(record, field) for field in
                  ("name", "record_type", "ttl", "routing_policy")}
        merged["values"] = old_values
        merged.update(payload.model_dump(exclude_unset=True))
        validated = DNSRecordCreate.model_validate(merged)
        name, values = _validate(validated, zone, supplied_name="name" in payload.model_fields_set)
        _check_conflicts(db, zone_id, name, validated.record_type, record_id)
        fields = validated.model_dump(exclude={"values"})
        fields["name"] = name
        changed = any(getattr(record, field) != value for field, value in fields.items())
        if changed or values != old_values:
            for field, value in fields.items():
                setattr(record, field, value)
            if values != old_values:
                # Delete the old collection before inserting positions 0..N.
                # Expire it so ORM relationship handling cannot null old FKs.
                db.exec(delete(DNSRecordValue).where(DNSRecordValue.record_set_id == record_id))
                db.expire(record, ["values"])
                record.values = [
                    DNSRecordValue(position=position, value=value)
                    for position, value in enumerate(values)
                ]
            record.updated_at = utc_now()
            db.add(record)
            db.flush()
        response = _response(record, zone)
    return response


def delete_record(db: Session, user_id: UUID, zone_id: UUID, record_id: UUID) -> None:
    with _write_transaction(db):
        get_owned_zone(db, user_id, zone_id)
        db.delete(_get_record(db, zone_id, record_id))
