"""Persistent session metadata; raw tokens are never stored in this table."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from app.models.common import UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key="users.id", ondelete="CASCADE", index=True, nullable=False
    )
    token_hash: str = Field(unique=True, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=UTCDateTime,
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )
    expires_at: datetime = Field(sa_type=UTCDateTime, index=True, nullable=False)

    user: "User" = Relationship(back_populates="sessions")
