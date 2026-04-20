from typing import Any, Literal


class EasyStoryError(Exception):
    """Base exception for shared runtime failures."""


class BusinessError(EasyStoryError):
    """Base exception for service-layer business failures."""

    status_code = 400
    code = "business_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(BusinessError):
    status_code = 404
    code = "not_found"


class ConflictError(BusinessError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(BusinessError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(BusinessError):
    status_code = 403
    code = "forbidden"


class BusinessRuleError(BusinessError):
    status_code = 422
    code = "business_rule_error"


class ConfigurationError(EasyStoryError):
    """Raised when repository or runtime configuration is invalid."""


class UpstreamServiceError(ConfigurationError):
    """Raised when an upstream LLM service returns a non-local runtime failure."""


class UpstreamAuthenticationError(UpstreamServiceError):
    """Raised when upstream authentication fails."""


class UpstreamRateLimitError(UpstreamServiceError):
    """Raised when upstream rate limiting rejects the request."""


class UpstreamTimeoutError(UpstreamServiceError):
    """Raised when the upstream request times out."""


class UnknownModelError(ConfigurationError):
    def __init__(self, model: str):
        super().__init__(f"Unknown model: {model}")
        self.model = model


class BudgetExceededError(EasyStoryError):
    """Raised when a budget guard refuses execution."""

    def __init__(
        self,
        message: str,
        *,
        action: Literal["pause", "skip", "fail"],
        scope: str,
        used_tokens: int,
        limit_tokens: int,
        usage_type: str,
        raw_output: dict[str, Any],
        partial_aggregated_review: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.action = action
        self.scope = scope
        self.used_tokens = used_tokens
        self.limit_tokens = limit_tokens
        self.usage_type = usage_type
        self.raw_output = raw_output
        self.partial_aggregated_review = partial_aggregated_review


class ModelFallbackExhaustedError(EasyStoryError):
    """Raised when all explicit model candidates are exhausted."""

    def __init__(
        self,
        message: str,
        *,
        action: Literal["pause", "fail"],
        attempted_models: list[str],
        skipped_models: list[str] | None = None,
        last_error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.action = action
        self.attempted_models = attempted_models
        self.skipped_models = skipped_models or []
        self.last_error = last_error
