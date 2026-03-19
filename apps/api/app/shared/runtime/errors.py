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


class BusinessRuleError(BusinessError):
    status_code = 422
    code = "business_rule_error"


class ConfigurationError(EasyStoryError):
    """Raised when repository or runtime configuration is invalid."""


class UnknownModelError(ConfigurationError):
    def __init__(self, model: str):
        super().__init__(f"Unknown model: {model}")
        self.model = model


class BudgetExceededError(EasyStoryError):
    """Raised when a budget guard refuses execution."""
