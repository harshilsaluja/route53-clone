"""Reusable session-derived identity and basic mutation-Origin validation."""

from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session as DatabaseSession

from app.config import Settings
from app.database import get_session
from app.errors import APIError
from app.models import User
from app.services.auth_service import AuthenticatedSession, authenticate


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_session(
    request: Request,
    db: Annotated[DatabaseSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> AuthenticatedSession:
    return authenticate(db, request.cookies.get(settings.session_cookie_name))


def get_current_user(
    identity: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> User:
    return identity.user


def require_allowed_origin(
    request: Request,
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> None:
    origin = request.headers.get("origin")
    # CLI clients may omit Origin; the same-origin API docs also remain usable.
    same_origin = str(request.base_url).rstrip("/")
    if origin is not None and origin not in [same_origin, *settings.allowed_frontend_origins]:
        raise APIError(403, "ORIGIN_NOT_ALLOWED", "Request origin is not allowed.")
