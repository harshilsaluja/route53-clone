"""Database-backed session lifecycle, independent of HTTP cookies."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session as DatabaseSession, select

from app.errors import APIError
from app.models import Session, User
from app.models.common import utc_now
from app.normalization import normalize_email
from app.security import (
    dummy_password_hash, generate_session_token, hash_session_token,
    is_session_token, verify_password,
)


@dataclass
class AuthenticatedSession:
    user: User
    session: Session


def login(
    db: DatabaseSession, email: str, password: str, ttl_seconds: int
) -> tuple[AuthenticatedSession, str]:
    user = db.exec(select(User).where(User.email == normalize_email(email))).first()
    password_hash = user.password_hash if user else dummy_password_hash()
    verified = verify_password(password, password_hash)
    if user is None or not verified:
        raise APIError(401, "INVALID_CREDENTIALS", "Invalid email or password.")

    token = generate_session_token()
    now = utc_now()
    session = Session(user_id=user.id, token_hash=hash_session_token(token),
                      created_at=now, expires_at=now + timedelta(seconds=ttl_seconds))
    try:
        db.add(session)
        db.commit()
        db.refresh(session)
    except SQLAlchemyError:
        db.rollback()
        raise
    return AuthenticatedSession(user=user, session=session), token


def authenticate(db: DatabaseSession, token: str | None) -> AuthenticatedSession:
    if is_session_token(token):
        session = db.exec(select(Session).where(
            Session.token_hash == hash_session_token(token),
            Session.expires_at > utc_now(),
        )).first()
        if session is not None:
            user = db.get(User, session.user_id)
            if user is not None:
                return AuthenticatedSession(user=user, session=session)
    raise APIError(401, "UNAUTHORIZED", "A valid session is required.")


def logout(db: DatabaseSession, token: str | None) -> None:
    if not is_session_token(token):
        return
    try:
        # Also revokes an expired session if the browser still sends its token.
        db.exec(delete(Session).where(Session.token_hash == hash_session_token(token)))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
