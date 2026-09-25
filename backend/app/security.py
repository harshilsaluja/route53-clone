"""Password hashing and opaque-token primitives; no persistence or HTTP concerns."""

import hashlib
import re
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    """Unknown accounts still perform password verification, without import work."""
    return hash_password("not-a-user-password")


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    # SHA-256 is appropriate for random 256-bit tokens, never for user passwords.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_session_token(token: str | None) -> bool:
    return token is not None and re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is not None
