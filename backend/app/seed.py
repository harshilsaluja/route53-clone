"""Explicit demo account provisioning: python -m app.seed (after migrations)."""

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session as DatabaseSession, select

from app.database import engine
from app.models import User
from app.normalization import normalize_email
from app.security import hash_password

# Public assignment credentials, not production secrets.
DEMO_EMAIL = "demo@route53clone.dev"
DEMO_PASSWORD = "Scaler@123"
DEMO_DISPLAY_NAME = "Demo User"


def seed_demo_user(db: DatabaseSession) -> tuple[User, bool]:
    email = normalize_email(DEMO_EMAIL)
    existing = db.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        return existing, False
    user = User(email=email, password_hash=hash_password(DEMO_PASSWORD),
                display_name=DEMO_DISPLAY_NAME)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        # Concurrent seed invocations must not duplicate or overwrite an account.
        existing = db.exec(select(User).where(User.email == email)).first()
        if existing is not None:
            return existing, False
        raise
    except SQLAlchemyError:
        db.rollback()
        raise
    return user, True


def main() -> None:
    with DatabaseSession(engine) as db:
        _, created = seed_demo_user(db)
    print("Demo user created." if created else "Demo user already exists; unchanged.")


if __name__ == "__main__":
    main()
