"""Small, safe API error envelope without request-body or database-detail leakage."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default errors include input values, which can contain passwords.
        details = [
            {"field": ".".join(str(part) for part in error["loc"]),
             "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR",
                               "message": "Please correct the submitted fields.",
                               "details": details}},
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        # Do not include SQL, bound parameters, or internal exception details.
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR",
                               "message": "Unable to complete the request."}},
            headers={"Cache-Control": "no-store"},
        )
