"""Environment configuration with a stable backend-relative .env location."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "AWS Route 53 Clone API"
    database_url: str = "sqlite:///./route53.db"
    allowed_frontend_origins: list[str] = ["http://localhost:3000"]
    session_cookie_name: str = Field(default="route53_session", pattern=r"^[A-Za-z0-9_]+$")
    session_ttl_seconds: int = Field(default=86400, gt=0)
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("allowed_frontend_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        normalized = []
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"} or not parsed.hostname
                or "*" in origin or parsed.username or parsed.password
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            ):
                raise ValueError("Origins must be explicit HTTP(S) origins without paths.")
            normalized.append(origin.rstrip("/"))
        return normalized

    @model_validator(mode="after")
    def validate_cookie_security(self) -> "Settings":
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SameSite=None requires Secure cookies.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
