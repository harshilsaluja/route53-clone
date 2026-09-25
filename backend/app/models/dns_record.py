"""A logical record set owns ordered, individually stored values."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum, Index, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.common import TimestampedModel
from app.models.enums import DNSRecordType, RoutingPolicy

if TYPE_CHECKING:
    from app.models.hosted_zone import HostedZone


class DNSRecordSet(TimestampedModel, table=True):
    __tablename__ = "dns_record_sets"
    __table_args__ = (
        UniqueConstraint("hosted_zone_id", "name", "record_type",
                         name="uq_dns_record_sets_zone_name_type"),
        Index("ix_dns_record_sets_zone_type", "hosted_zone_id", "record_type"),
        CheckConstraint("ttl > 0", name="ck_dns_record_sets_ttl_positive"),
        CheckConstraint(
            "name = lower(trim(name)) AND name NOT LIKE '%.'",
            name="ck_dns_record_sets_name_normalized",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hosted_zone_id: UUID = Field(
        foreign_key="hosted_zones.id", ondelete="CASCADE", nullable=False
    )
    name: str = Field(nullable=False)
    record_type: DNSRecordType = Field(
        sa_type=Enum(DNSRecordType, native_enum=False, create_constraint=True,
                     name="ck_dns_record_sets_record_type"),
        nullable=False,
    )
    ttl: int = Field(nullable=False)
    routing_policy: RoutingPolicy = Field(
        default=RoutingPolicy.SIMPLE,
        sa_type=Enum(RoutingPolicy, native_enum=False, create_constraint=True,
                     name="ck_dns_record_sets_routing_policy"),
        nullable=False,
        sa_column_kwargs={"server_default": "SIMPLE"},
    )

    hosted_zone: "HostedZone" = Relationship(back_populates="records")
    values: list["DNSRecordValue"] = Relationship(
        back_populates="record_set",
        passive_deletes="all",
        sa_relationship_kwargs={"order_by": "DNSRecordValue.position"},
    )


class DNSRecordValue(SQLModel, table=True):
    __tablename__ = "dns_record_values"
    __table_args__ = (
        UniqueConstraint("record_set_id", "position",
                         name="uq_dns_record_values_set_position"),
        CheckConstraint("position >= 0", name="ck_dns_record_values_position_nonnegative"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    record_set_id: UUID = Field(
        foreign_key="dns_record_sets.id", ondelete="CASCADE", nullable=False
    )
    position: int = Field(nullable=False)
    value: str = Field(sa_type=Text, nullable=False)

    record_set: DNSRecordSet = Relationship(back_populates="values")
