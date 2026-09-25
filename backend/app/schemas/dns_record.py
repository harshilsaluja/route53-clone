"""DNS record request validation and public response shapes."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DNSRecordType, RoutingPolicy
from app.schemas.common import PaginationMetadata

RecordName = Annotated[str, Field(max_length=253)]
TTL = Annotated[int, Field(strict=True, ge=1, le=2147483647)]
RecordValues = Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]


class DNSRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: RecordName
    record_type: DNSRecordType
    ttl: TTL
    routing_policy: RoutingPolicy = RoutingPolicy.SIMPLE
    values: RecordValues


class DNSRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: RecordName | None = None
    record_type: DNSRecordType | None = None
    ttl: TTL | None = None
    routing_policy: RoutingPolicy | None = None
    values: RecordValues | None = None

    @model_validator(mode="after")
    def validate_partial_update(self) -> "DNSRecordUpdate":
        if not self.model_fields_set:
            raise ValueError("Supply at least one editable field.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Record fields cannot be null.")
        return self


class DNSRecordListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=1024)
    record_type: DNSRecordType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Literal["name", "record_type", "ttl", "created_at"] = "name"
    sort_order: Literal["asc", "desc"] = "asc"


class DNSRecordResponse(BaseModel):
    id: UUID
    hosted_zone_id: UUID
    name: str
    fqdn: str
    record_type: DNSRecordType
    ttl: int
    routing_policy: RoutingPolicy
    values: list[str]
    created_at: datetime
    updated_at: datetime


class DNSRecordListResponse(BaseModel):
    items: list[DNSRecordResponse]
    pagination: PaginationMetadata
