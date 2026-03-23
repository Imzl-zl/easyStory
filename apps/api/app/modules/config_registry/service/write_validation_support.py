from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.shared.runtime.errors import BusinessRuleError

ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_config_model(model_type: type[ModelT], document: dict[str, Any]) -> ModelT:
    try:
        return model_type.model_validate(document)
    except ValidationError as exc:
        raise BusinessRuleError(_format_validation_error(exc)) from exc


def _format_validation_error(exc: ValidationError) -> str:
    return "; ".join(_format_error(error) for error in exc.errors())


def _format_error(error: dict[str, Any]) -> str:
    location = _format_location(error.get("loc", ()))
    message = error.get("msg", "Invalid input")
    if not location:
        return message
    return f"{location}: {message}"


def _format_location(location: tuple[Any, ...] | list[Any]) -> str:
    parts = [str(part) for part in location if part != "__root__"]
    return ".".join(parts)
