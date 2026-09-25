"""Authentication HTTP contract; services own persistence and verification."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DatabaseSession

from app.config import Settings
from app.database import get_session
from app.dependencies import (
    get_current_session, get_current_user, get_runtime_settings, require_allowed_origin,
)
from app.models import User
from app.schemas.auth import LoginRequest, SafeUserResponse, SessionResponse
from app.services import auth_service
from app.services.auth_service import AuthenticatedSession

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
Database = Annotated[DatabaseSession, Depends(get_session)]
Configuration = Annotated[Settings, Depends(get_runtime_settings)]


@router.post("/login", response_model=SessionResponse,
             dependencies=[Depends(require_allowed_origin)])
def login(payload: LoginRequest, response: Response, db: Database,
          settings: Configuration) -> SessionResponse:
    identity, token = auth_service.login(
        db, payload.email, payload.password.get_secret_value(), settings.session_ttl_seconds
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
        max_age=settings.session_ttl_seconds,
        expires=identity.session.expires_at,
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(user=SafeUserResponse.model_validate(identity.user),
                           expires_at=identity.session.expires_at)


@router.get("/me", response_model=SessionResponse)
def me(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    identity: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> SessionResponse:
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(user=SafeUserResponse.model_validate(user),
                           expires_at=identity.session.expires_at)


@router.post("/logout", status_code=204, dependencies=[Depends(require_allowed_origin)])
def logout(request: Request, db: Database, settings: Configuration) -> Response:
    auth_service.logout(db, request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        key=settings.session_cookie_name, path="/",
        httponly=True, secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return response
