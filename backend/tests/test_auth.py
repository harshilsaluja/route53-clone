"""Authentication uses the same migrated temporary databases as database tests."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session as DatabaseSession, select

from app.config import Settings
from app.database import create_sqlite_engine, get_session
from app.dependencies import get_current_user
from app.main import create_app
from app.models import Session, User
from app.models.common import utc_now
from app.security import generate_session_token, hash_password, hash_session_token, verify_password
from app.seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_user
from app.services import auth_service

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        _env_file=None, allowed_frontend_origins=["http://localhost:3000"],
        session_cookie_name="route53_session", session_cookie_secure=False,
        session_cookie_samesite="lax", session_ttl_seconds=86400,
    )


@pytest.fixture
def auth_app(db_engine: Engine, auth_settings: Settings) -> FastAPI:
    application = create_app(auth_settings)

    def isolated_session() -> Generator[DatabaseSession, None, None]:
        with DatabaseSession(db_engine) as db:
            yield db

    application.dependency_overrides[get_session] = isolated_session
    return application


@pytest.fixture
def client(auth_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(auth_app, base_url="http://localhost:8000") as test_client:
        yield test_client


@pytest.fixture
def demo_user(db_engine: Engine) -> UUID:
    with DatabaseSession(db_engine) as db:
        user, _ = seed_demo_user(db)
        return user.id


def login(client: TestClient):
    return client.post(LOGIN, json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})


def test_seed_is_idempotent_and_hashes_password(db_engine: Engine) -> None:
    with DatabaseSession(db_engine) as db:
        first, created = seed_demo_user(db)
        assert created
        original_hash = first.password_hash
        assert original_hash != DEMO_PASSWORD
        assert original_hash.startswith("$argon2id$")
        assert verify_password(DEMO_PASSWORD, original_hash)
        first.display_name = "Keep this change"
        db.commit()
        second, created_again = seed_demo_user(db)
        assert not created_again
        assert second.id == first.id
        assert second.password_hash == original_hash
        assert second.display_name == "Keep this change"
        assert len(db.exec(select(User)).all()) == 1


def test_seed_does_not_reset_existing_password(db_engine: Engine) -> None:
    with DatabaseSession(db_engine) as db:
        user, _ = seed_demo_user(db)
        changed_hash = hash_password("a-different-demo-password")
        user.password_hash = changed_hash
        db.commit()
        seeded, created = seed_demo_user(db)
        assert not created
        assert seeded.password_hash == changed_hash


def test_login_cookie_response_and_persisted_hash(
    client: TestClient, demo_user: UUID, db_engine: Engine, auth_settings: Settings
) -> None:
    before = utc_now()
    response = login(client)
    after = utc_now()
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user", "expires_at"}
    assert body["user"] == {
        "id": str(demo_user), "email": DEMO_EMAIL, "display_name": "Demo User",
    }
    token = client.cookies.get(auth_settings.session_cookie_name)
    assert token and len(token) == 43
    for private_value in ("password_hash", "token_hash", token, DEMO_PASSWORD):
        assert private_value not in response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Max-Age=86400" in cookie and "Secure" not in cookie and "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"
    expires_at = datetime.fromisoformat(body["expires_at"])
    with DatabaseSession(db_engine) as db:
        [session] = db.exec(select(Session)).all()
        assert session.user_id == demo_user
        assert session.token_hash == hash_session_token(token)
        assert session.token_hash != token
        assert len(session.token_hash) == 64
        assert session.expires_at == expires_at
        assert session.expires_at - session.created_at == timedelta(hours=24)
        assert before <= session.created_at <= after
        assert session.expires_at.tzinfo == UTC
    from http.cookies import SimpleCookie
    parsed = SimpleCookie()
    parsed.load(cookie)
    cookie_expiry = parsedate_to_datetime(parsed[auth_settings.session_cookie_name]["expires"])
    assert abs((cookie_expiry - expires_at).total_seconds()) < 1


def test_login_normalizes_email(client: TestClient, demo_user: UUID) -> None:
    response = client.post(LOGIN, json={"email": " DEMO@ROUTE53CLONE.DEV ", "password": DEMO_PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(demo_user)


def test_invalid_credentials_are_indistinguishable(
    client: TestClient, demo_user: UUID, db_engine: Engine
) -> None:
    wrong = client.post(LOGIN, json={"email": DEMO_EMAIL, "password": "incorrect"})
    unknown = client.post(LOGIN, json={"email": "unknown@example.com", "password": "incorrect"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {
        "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}
    }
    assert "set-cookie" not in wrong.headers and "set-cookie" not in unknown.headers
    with DatabaseSession(db_engine) as db:
        assert db.exec(select(Session)).all() == []


def test_me_restores_safe_identity_and_does_not_extend_expiry(
    client: TestClient, demo_user: UUID
) -> None:
    initial = login(client)
    response = client.get(ME)
    assert response.status_code == 200
    assert response.json() == initial.json()
    assert "set-cookie" not in response.headers
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("cookie", [None, "invalid", "x" * 43])
def test_me_rejects_missing_or_invalid_cookie(client: TestClient, cookie: str | None) -> None:
    if cookie is not None:
        client.cookies.set("route53_session", cookie)
    response = client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_cookie_cannot_authenticate(
    client: TestClient, demo_user: UUID, db_engine: Engine
) -> None:
    assert login(client).status_code == 200
    with DatabaseSession(db_engine) as db:
        session = db.exec(select(Session)).one()
        session.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    assert client.get(ME).status_code == 401
    assert client.get(ME).status_code == 401
    assert client.post(LOGOUT).status_code == 204
    with DatabaseSession(db_engine) as db:
        assert db.exec(select(Session)).all() == []


def test_session_is_invalid_at_exact_expiration(
    client: TestClient, demo_user: UUID, db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    login(client)
    with DatabaseSession(db_engine) as db:
        expiry = db.exec(select(Session)).one().expires_at
    monkeypatch.setattr(auth_service, "utc_now", lambda: expiry)
    assert client.get(ME).status_code == 401


def test_logout_revokes_cookie_and_replay(
    client: TestClient, demo_user: UUID, db_engine: Engine
) -> None:
    login(client)
    token = client.cookies.get("route53_session")
    response = client.post(LOGOUT)
    assert response.status_code == 204 and response.content == b""
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Path=/" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert client.cookies.get("route53_session") is None
    with DatabaseSession(db_engine) as db:
        assert db.exec(select(Session)).all() == []
    client.cookies.set("route53_session", token)
    assert client.get(ME).status_code == 401
    assert client.post(LOGOUT).status_code == 204


@pytest.mark.parametrize("cookie", [None, "invalid", "x" * 43])
def test_logout_is_idempotent(client: TestClient, cookie: str | None) -> None:
    if cookie is not None:
        client.cookies.set("route53_session", cookie)
    for _ in range(2):
        response = client.post(LOGOUT)
        assert response.status_code == 204
        assert "Max-Age=0" in response.headers["set-cookie"]


def test_independent_login_sessions(
    client: TestClient, demo_user: UUID, db_engine: Engine
) -> None:
    login(client)
    first_token = client.cookies.get("route53_session")
    login(client)
    second_token = client.cookies.get("route53_session")
    assert first_token != second_token
    with DatabaseSession(db_engine) as db:
        assert len(db.exec(select(Session)).all()) == 2
    assert client.post(LOGOUT).status_code == 204
    client.cookies.set("route53_session", first_token)
    assert client.get(ME).status_code == 200


def test_session_identity_cannot_be_selected_by_caller(
    client: TestClient, demo_user: UUID, db_engine: Engine
) -> None:
    with DatabaseSession(db_engine) as db:
        another = User(email="other@example.com", display_name="Other",
                       password_hash=hash_password("other-password"))
        db.add(another)
        db.commit()
        other_id = another.id
    login(client)
    response = client.get(ME, params={"user_id": str(other_id)},
                          headers={"X-User-ID": str(other_id)})
    assert response.json()["user"]["id"] == str(demo_user)
    response = client.post(LOGIN, json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD,
                                       "user_id": str(other_id)})
    assert response.status_code == 422


def test_current_user_dependency_returns_user(
    auth_app: FastAPI, client: TestClient, demo_user: UUID
) -> None:
    # Test-only endpoint; no extra API is registered in the application source.
    @auth_app.get("/_test/current-user")
    def identity(user: Annotated[User, Depends(get_current_user)]):
        return {"id": str(user.id)}

    assert client.get("/_test/current-user").status_code == 401
    login(client)
    assert client.get("/_test/current-user").json() == {"id": str(demo_user)}


def test_sessions_survive_new_app_and_database_connection(
    client: TestClient, demo_user: UUID, db_engine: Engine, auth_settings: Settings
) -> None:
    initial = login(client)
    token = client.cookies.get("route53_session")
    fresh_engine = create_sqlite_engine(db_engine.url)
    fresh_app = create_app(auth_settings)

    def fresh_db():
        with DatabaseSession(fresh_engine) as db:
            yield db

    fresh_app.dependency_overrides[get_session] = fresh_db
    try:
        with TestClient(fresh_app, base_url="http://localhost:8000") as fresh_client:
            fresh_client.cookies.set("route53_session", token)
            restored = fresh_client.get(ME)
            assert restored.status_code == 200
            assert restored.json() == initial.json()
    finally:
        fresh_engine.dispose()


def test_allowed_credentialed_cors(client: TestClient) -> None:
    response = client.options(LOGIN, headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unapproved_cors_origin(client: TestClient) -> None:
    response = client.options(LOGIN, headers={
        "Origin": "https://unapproved.example",
        "Access-Control-Request-Method": "POST",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:8000"])
def test_allowed_mutation_origin(client: TestClient, demo_user: UUID, origin: str) -> None:
    response = client.post(LOGIN, json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                           headers={"Origin": origin})
    assert response.status_code == 200
    assert client.post(LOGOUT, headers={"Origin": origin}).status_code == 204


@pytest.mark.parametrize("origin", ["https://unapproved.example", "null"])
def test_rejected_mutation_origin(
    client: TestClient, demo_user: UUID, db_engine: Engine, origin: str
) -> None:
    response = client.post(LOGIN, json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                           headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
    assert client.post(LOGOUT, headers={"Origin": origin}).status_code == 403
    with DatabaseSession(db_engine) as db:
        assert db.exec(select(Session)).all() == []


def test_cors_headers_on_auth_error(client: TestClient) -> None:
    response = client.get(ME, headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_secure_cookie_configuration(
    auth_app: FastAPI, auth_settings: Settings, demo_user: UUID
) -> None:
    auth_settings.session_cookie_secure = True
    auth_settings.session_cookie_samesite = "none"
    with TestClient(auth_app, base_url="https://localhost:8000") as secure_client:
        response = login(secure_client)
        assert "Secure" in response.headers["set-cookie"]
        assert "SameSite=none" in response.headers["set-cookie"]
        assert secure_client.get(ME).status_code == 200
        response = secure_client.post(LOGOUT)
        assert "Secure" in response.headers["set-cookie"]
        assert "SameSite=none" in response.headers["set-cookie"]


@pytest.mark.parametrize("values", [
    {"allowed_frontend_origins": ["*"]},
    {"allowed_frontend_origins": ["https://example.com/path"]},
    {"session_cookie_samesite": "none", "session_cookie_secure": False},
    {"session_ttl_seconds": 0},
])
def test_unsafe_configuration_rejected(values: dict) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("payload", [
    {"email": "invalid", "password": "sensitive-password"},
    {"email": DEMO_EMAIL, "password": ""},
    {"email": DEMO_EMAIL, "password": {"unexpected": "sensitive-password"}},
    {"email": DEMO_EMAIL, "password": "sensitive-password", "extra": "secret"},
])
def test_validation_is_safe(client: TestClient, payload: dict) -> None:
    response = client.post(LOGIN, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "sensitive-password" not in response.text
    assert '"input"' not in response.text


def test_health_unchanged(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_password_verification_and_token_primitives() -> None:
    password_hash = hash_password("test-password")
    assert verify_password("test-password", password_hash)
    assert not verify_password("wrong", password_hash)
    assert not verify_password("test-password", "not-an-argon-hash")
    one, two = generate_session_token(), generate_session_token()
    assert one != two
    assert len(one) == len(two) == 43
    assert hash_session_token(one) != one


@pytest.mark.parametrize("operation", ["login", "logout"])
def test_failed_commits_rollback(
    db_engine: Engine, demo_user: UUID, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    with DatabaseSession(db_engine) as db:
        identity, token = auth_service.login(db, DEMO_EMAIL, DEMO_PASSWORD, 86400)
        session_id = identity.session.id
    with DatabaseSession(db_engine) as db:
        def fail_commit():
            raise SQLAlchemyError("simulated write failure")
        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(SQLAlchemyError):
            if operation == "login":
                auth_service.login(db, DEMO_EMAIL, DEMO_PASSWORD, 86400)
            else:
                auth_service.logout(db, token)
        assert not db.in_transaction()
    with DatabaseSession(db_engine) as db:
        [session] = db.exec(select(Session)).all()
        assert session.id == session_id


def test_database_error_response_does_not_leak_details(
    client: TestClient, demo_user: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args, **kwargs):
        raise SQLAlchemyError("private database and token details")
    monkeypatch.setattr(auth_service, "login", fail)
    response = login(client)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private database" not in response.text
