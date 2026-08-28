"""FastAPI exception handlers — separate from exception definitions."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import AppError
from .response import error_response, validation_error_response
from .schemas import Envelope, EnvelopeMeta, ErrorDetail

_HTTP_STATUS_TO_ERROR_CODE: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        envelope = error_response(exc, request)
        return JSONResponse(
            status_code=exc.status_code, content=envelope.model_dump(mode="json")
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            ErrorDetail(
                code="validation_error",
                message=err["msg"],
                field=".".join(str(loc) for loc in err["loc"]) if err["loc"] else None,
            )
            for err in exc.errors()
        ]
        envelope = validation_error_response(errors, request=request)
        return JSONResponse(
            status_code=422, content=envelope.model_dump(mode="json")
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        meta = EnvelopeMeta(request_id=request_id)
        error_code = _HTTP_STATUS_TO_ERROR_CODE.get(exc.status_code, "http_error")
        envelope: Envelope[None] = Envelope(
            success=False,
            data=None,
            message=exc.detail,
            errors=[ErrorDetail(code=error_code, message=exc.detail)],
            meta=meta,
        )
        return JSONResponse(
            status_code=exc.status_code, content=envelope.model_dump(mode="json")
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        envelope = error_response(exc, request)
        return JSONResponse(
            status_code=500, content=envelope.model_dump(mode="json")
        )
