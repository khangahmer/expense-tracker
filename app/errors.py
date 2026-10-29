import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("expense_tracker")


class AppError(Exception):
    """An error we expected, with a status code we chose."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: int) -> None:
        super().__init__(404, "not_found", f"{resource} {resource_id} not found")


def error_response(
    status_code: int, code: str, message: str, details: object | None = None
) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return error_response(exc.status_code, f"http_{exc.status_code}", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return error_response(
            422, "validation_error", "Request validation failed", details
        )

    
    

    @app.exception_handler(OperationalError)
    async def handle_db_unavailable(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        logger.error("database unavailable: %s", exc.orig)
        return error_response(
            503, "database_unavailable", "The database is temporarily unavailable"
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        error_id = uuid.uuid4().hex[:8]
        logger.error(
            "unhandled error %s on %s %s",
            error_id,
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return error_response(
            500,
            "internal_error",
            "Something went wrong on our side",
            {"error_id": error_id},
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
            request: Request, exc: IntegrityError
        ) -> JSONResponse:
        if getattr(exc.orig, "sqlstate", None) == "23505":  # unique violation
            logger.warning("duplicate value: %s", exc.orig)
            return error_response(409, "conflict", "That value already exists")
        # Anything else means our own validation missed something: our bug.
        return await handle_unexpected(request, exc)