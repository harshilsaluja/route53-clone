"""Authenticated record endpoints nested under an owned Hosted Zone."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user, require_allowed_origin
from app.models import User
from app.schemas.dns_record import (
    DNSRecordCreate, DNSRecordListQuery, DNSRecordListResponse,
    DNSRecordResponse, DNSRecordUpdate,
)
from app.services import dns_record_service


def _disable_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/v1/hosted-zones/{zone_id}/records", tags=["DNS Records"],
    dependencies=[Depends(_disable_caching)],
)
Database = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=DNSRecordListResponse)
def list_records(
    zone_id: UUID, db: Database, user: CurrentUser,
    query: Annotated[DNSRecordListQuery, Query()],
) -> DNSRecordListResponse:
    return dns_record_service.list_records(db, user.id, zone_id, query)


@router.post("", response_model=DNSRecordResponse, status_code=201,
             dependencies=[Depends(require_allowed_origin)])
def create_record(
    zone_id: UUID, payload: DNSRecordCreate, db: Database, user: CurrentUser,
) -> DNSRecordResponse:
    return dns_record_service.create_record(db, user.id, zone_id, payload)


@router.get("/{record_id}", response_model=DNSRecordResponse)
def get_record(
    zone_id: UUID, record_id: UUID, db: Database, user: CurrentUser,
) -> DNSRecordResponse:
    return dns_record_service.get_record(db, user.id, zone_id, record_id)


@router.patch("/{record_id}", response_model=DNSRecordResponse,
              dependencies=[Depends(require_allowed_origin)])
def update_record(
    zone_id: UUID, record_id: UUID, payload: DNSRecordUpdate, db: Database, user: CurrentUser,
) -> DNSRecordResponse:
    return dns_record_service.update_record(db, user.id, zone_id, record_id, payload)


@router.delete("/{record_id}", status_code=204, dependencies=[Depends(require_allowed_origin)])
def delete_record(zone_id: UUID, record_id: UUID, db: Database, user: CurrentUser) -> Response:
    dns_record_service.delete_record(db, user.id, zone_id, record_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
