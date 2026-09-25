"""Hosted zones own relative DNS record names."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum, Index, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.common import TimestampedModel
from app.models.enums import HostedZoneType

if TYPE_CHECKING:
    from app.models.dns_record import DNSRecordSet
    from app.models.user import User


class HostedZone(TimestampedModel, table=True):
    __tablename__ = "hosted_zones"
    __table_args__ = (
        UniqueConstraint("user_id", "name", "type", name="uq_hosted_zones_owner_name_type"),
        Index("ix_hosted_zones_user_type", "user_id", "type"),
        CheckConstraint(
            "name = lower(trim(name)) AND length(name) > 0 AND name NOT LIKE '%.'",
            name="ck_hosted_zones_name_normalized",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", nullable=False)
    name: str = Field(nullable=False)
    type: HostedZoneType = Field(
        sa_type=Enum(HostedZoneType, native_enum=False, create_constraint=True,
                     name="ck_hosted_zones_type"),
        nullable=False,
    )
    comment: str | None = Field(default=None)

    user: "User" = Relationship(back_populates="hosted_zones")
    records: list["DNSRecordSet"] = Relationship(
        back_populates="hosted_zone", passive_deletes="all"
    )
