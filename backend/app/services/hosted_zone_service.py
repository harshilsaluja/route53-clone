"""Owner-scoped Hosted Zone CRUD and SQL-based collection queries."""

import sqlite3
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, col, select

from app.errors import APIError
from app.models import DNSRecordSet, HostedZone
from app.schemas.common import PaginationMetadata
from app.schemas.hosted_zone import (
    HostedZoneCreate, HostedZoneListQuery, HostedZoneListResponse,
    HostedZoneResponse, HostedZoneUpdate,
)


def _get_owned_zone(db: Session, user_id: UUID, zone_id: UUID) -> HostedZone:
    zone = db.exec(select(HostedZone).where(
        HostedZone.id == zone_id, HostedZone.user_id == user_id,
    )).first()
    if zone is None:
        raise APIError(404, "HOSTED_ZONE_NOT_FOUND", "Hosted zone was not found.")
    return zone


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Translate only this specific uniqueness rule; other failures stay 500.
        if (
            isinstance(exc.orig, sqlite3.IntegrityError)
            and getattr(exc.orig, "sqlite_errorcode", None) == sqlite3.SQLITE_CONSTRAINT_UNIQUE
            and str(exc.orig) == (
                "UNIQUE constraint failed: hosted_zones.user_id, "
                "hosted_zones.name, hosted_zones.type"
            )
        ):
            raise APIError(
                409, "HOSTED_ZONE_ALREADY_EXISTS",
                "A hosted zone with this name and type already exists.",
            ) from None
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def _response(zone: HostedZone, record_count: int = 0) -> HostedZoneResponse:
    return HostedZoneResponse.model_validate(zone).model_copy(
        update={"record_count": record_count}
    )


def create_zone(db: Session, user_id: UUID, payload: HostedZoneCreate) -> HostedZoneResponse:
    zone = HostedZone(user_id=user_id, **payload.model_dump())
    db.add(zone)
    _commit(db)
    db.refresh(zone)
    return _response(zone)


def get_zone(db: Session, user_id: UUID, zone_id: UUID) -> HostedZoneResponse:
    zone = _get_owned_zone(db, user_id, zone_id)
    count = db.exec(
        select(func.count(DNSRecordSet.id)).join(HostedZone).where(
            HostedZone.id == zone_id, HostedZone.user_id == user_id,
        )
    ).one()
    return _response(zone, count)


def list_zones(
    db: Session, user_id: UUID, query: HostedZoneListQuery
) -> HostedZoneListResponse:
    conditions = [HostedZone.user_id == user_id]
    search = query.search.strip()
    if search:
        # Escape LIKE wildcards so user-entered '%' and '_' are literal text.
        conditions.append(or_(
            col(HostedZone.name).icontains(search, autoescape=True),
            col(HostedZone.comment).icontains(search, autoescape=True),
        ))
    if query.type is not None:
        conditions.append(HostedZone.type == query.type)
    total = db.exec(select(func.count()).select_from(HostedZone).where(*conditions)).one()
    pagination = PaginationMetadata(
        page=query.page, page_size=query.page_size, total=total,
        pages=(total + query.page_size - 1) // query.page_size,
    )
    offset = (query.page - 1) * query.page_size
    if offset >= total:
        return HostedZoneListResponse(items=[], pagination=pagination)

    sort_column = {
        "name": HostedZone.name, "type": HostedZone.type,
        "created_at": HostedZone.created_at,
    }[query.sort_by]
    primary_order = sort_column.asc() if query.sort_order == "asc" else sort_column.desc()
    rows = db.exec(
        select(HostedZone, func.count(DNSRecordSet.id))
        .outerjoin(DNSRecordSet, DNSRecordSet.hosted_zone_id == HostedZone.id)
        .where(*conditions)
        .group_by(HostedZone)
        .order_by(primary_order, HostedZone.id.asc())
        .offset(offset).limit(query.page_size)
    ).all()
    return HostedZoneListResponse(
        items=[_response(zone, count) for zone, count in rows], pagination=pagination
    )


def update_zone(
    db: Session, user_id: UUID, zone_id: UUID, payload: HostedZoneUpdate
) -> HostedZoneResponse:
    zone = _get_owned_zone(db, user_id, zone_id)
    merged = {"name": zone.name, "type": zone.type, "comment": zone.comment}
    merged.update(payload.model_dump(exclude_unset=True))
    try:
        validated = HostedZoneCreate.model_validate(merged)
    except ValidationError:
        raise APIError(422, "VALIDATION_ERROR", "The resulting hosted zone is invalid.") from None
    # Relative record owner names and record target values are intentionally untouched.
    for field, value in validated.model_dump().items():
        setattr(zone, field, value)
    db.add(zone)
    _commit(db)
    return get_zone(db, user_id, zone_id)


def delete_zone(db: Session, user_id: UUID, zone_id: UUID) -> None:
    zone = _get_owned_zone(db, user_id, zone_id)
    db.delete(zone)
    _commit(db)
