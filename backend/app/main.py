import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import ai, auth, axis, data, health, learning, profile, tasks
from .core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
logger = logging.getLogger("axis.api")


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    duration_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Accept",
        "Authorization",
        "X-Requested-With",
        "Origin",
    ],
)


def _error_response(
    status_code: int, code: str, message: str, details: object | None = None
) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", "http_error"))
        message = str(exc.detail.get("message", "Request failed"))
        details = exc.detail.get("details")
    else:
        code, message, details = "http_error", str(exc.detail), None
    response = _error_response(exc.status_code, code, message, details)
    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"loc": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return _error_response(422, "validation_error", "Request validation failed", details)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception method=%s path=%s request_id=%s",
        request.method,
        request.url.path,
        getattr(request.state, "request_id", "unknown"),
        exc_info=exc,
    )
    return _error_response(500, "internal_server_error", "An unexpected error occurred")


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(data.router)
app.include_router(ai.router)
app.include_router(learning.router)
app.include_router(profile.router)
app.include_router(axis.router)
app.include_router(tasks.router)
