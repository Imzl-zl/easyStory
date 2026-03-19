from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.runtime.errors import BusinessError


async def handle_business_error(_: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.message},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BusinessError, handle_business_error)
