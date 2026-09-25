"""Authenticated Hosted Zone endpoints; database work stays in the service."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user, require_allowed_origin
from app.models import User
from app.schemas.hosted_zone import (
    HostedZoneCreate, HostedZoneListQuery, HostedZoneListResponse,
    HostedZoneResponse, HostedZoneUpdate,
)
from app.services import hosted_zone_service


def _disable_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/v1/hosted-zones", tags=["Hosted Zones"],
    dependencies=[Depends(_disable_caching)],
)
Database = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=HostedZoneListResponse)
def list_zones(
    db: Database, user: CurrentUser,
    query: Annotated[HostedZoneListQuery, Query()],
) -> HostedZoneListResponse:
    """List your zones with SQL search, filtering, sorting, and pagination."""
    return hosted_zone_service.list_zones(db, user.id, query)


@router.post("", response_model=HostedZoneResponse, status_code=201,
             dependencies=[Depends(require_allowed_origin)])
def create_zone(
    payload: HostedZoneCreate, db: Database, user: CurrentUser
) -> HostedZoneResponse:
    """Create a zone owned by the authenticated user; no AWS resources are created."""
    return hosted_zone_service.create_zone(db, user.id, payload)


@router.get("/{zone_id}", response_model=HostedZoneResponse)
def get_zone(zone_id: UUID, db: Database, user: CurrentUser) -> HostedZoneResponse:
    """Retrieve an owned zone with its number of record sets."""
    return hosted_zone_service.get_zone(db, user.id, zone_id)


@router.patch("/{zone_id}", response_model=HostedZoneResponse,
              dependencies=[Depends(require_allowed_origin)])
def update_zone(
    zone_id: UUID, payload: HostedZoneUpdate, db: Database, user: CurrentUser
) -> HostedZoneResponse:
    """Update name, comment, or type. Renames preserve record owners and targets."""
    return hosted_zone_service.update_zone(db, user.id, zone_id, payload)


@router.delete("/{zone_id}", status_code=204, dependencies=[Depends(require_allowed_origin)])
def delete_zone(zone_id: UUID, db: Database, user: CurrentUser) -> Response:
    """Delete an owned zone; database cascades remove its record sets and values."""
    hosted_zone_service.delete_zone(db, user.id, zone_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
