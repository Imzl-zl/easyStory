from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.runtime.errors import BusinessError, ConfigurationError


async def handle_business_error(_: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.message},
    )


async def handle_configuration_error(_: Request, exc: ConfigurationError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": "configuration_error", "detail": str(exc)},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BusinessError, handle_business_error)
    app.add_exception_handler(ConfigurationError, handle_configuration_error)
