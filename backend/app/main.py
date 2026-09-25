"""FastAPI entry point. Business functionality begins in later phases."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Process liveness only; does not initialize or migrate the database."""
    return {"status": "ok"}
