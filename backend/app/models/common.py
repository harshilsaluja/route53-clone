"""UTC timestamp handling for SQLite, which does not preserve timezone offsets."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Store naive UTC internally and return aware UTC; reject ambiguous inputs."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamps must be timezone-aware.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


class TimestampedModel(SQLModel):
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=UTCDateTime,
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=UTCDateTime,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": utc_now,
        },
    )
