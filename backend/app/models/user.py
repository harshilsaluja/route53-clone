"""User persistence only; authentication is implemented in a later phase."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship

from app.models.common import TimestampedModel

if TYPE_CHECKING:
    from app.models.hosted_zone import HostedZone
    from app.models.session import Session


class User(TimestampedModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email = lower(trim(email)) AND length(email) > 0",
            name="ck_users_email_normalized",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    display_name: str = Field(nullable=False)

    sessions: list["Session"] = Relationship(
        back_populates="user", passive_deletes="all"
    )
    hosted_zones: list["HostedZone"] = Relationship(
        back_populates="user", passive_deletes="all"
    )
