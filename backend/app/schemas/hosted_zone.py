"""Hosted Zone request/query validation and public response shapes."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import HostedZoneType
from app.schemas.common import PaginationMetadata
from app.validation.dns_names import validate_zone_name

ZoneName = Annotated[str, AfterValidator(validate_zone_name)]


class HostedZoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ZoneName
    type: HostedZoneType
    comment: str | None = Field(default=None, max_length=1024)


class HostedZoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ZoneName | None = None
    type: HostedZoneType | None = None
    comment: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def validate_partial_update(self) -> "HostedZoneUpdate":
        if not self.model_fields_set:
            raise ValueError("Supply at least one editable field.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null.")
        if "type" in self.model_fields_set and self.type is None:
            raise ValueError("Type cannot be null.")
        return self


class HostedZoneListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=1024)
    type: HostedZoneType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Literal["name", "type", "created_at"] = "name"
    sort_order: Literal["asc", "desc"] = "asc"


class HostedZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: HostedZoneType
    comment: str | None
    record_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class HostedZoneListResponse(BaseModel):
    items: list[HostedZoneResponse]
    pagination: PaginationMetadata
