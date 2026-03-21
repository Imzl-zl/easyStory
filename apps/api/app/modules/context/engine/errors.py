from __future__ import annotations

from app.shared.runtime.errors import BusinessRuleError


class ContextBuilderError(BusinessRuleError):
    """Base error for context building failures."""


class RequiredContextMissingError(ContextBuilderError):
    def __init__(self, inject_type: str):
        super().__init__(f"Required context missing: {inject_type}")
        self.inject_type = inject_type


class ContextOverflowError(ContextBuilderError):
    def __init__(
        self,
        limit_name: str,
        limit: int,
        total_tokens: int,
        blocking_sections: list[str],
    ):
        super().__init__(
            f"context_overflow ({limit_name}): total={total_tokens}, limit={limit}, "
            f"sections={', '.join(blocking_sections)}"
        )
        self.limit_name = limit_name
        self.limit = limit
        self.total_tokens = total_tokens
        self.blocking_sections = blocking_sections
