"""FastAPI entry point with backend session authentication."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.database import engine
from app.errors import register_error_handlers
from app.routers.auth import router as auth_router
from app.routers.hosted_zones import router as hosted_zones_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else get_settings()
    application = FastAPI(title=configuration.app_name, lifespan=lifespan)
    application.state.settings = configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=configuration.allowed_frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(application)
    application.include_router(auth_router)
    application.include_router(hosted_zones_router)

    @application.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        """Process liveness only; does not initialize or migrate the database."""
        return {"status": "ok"}

    return application


app = create_app()
