from __future__ import annotations

from dataclasses import replace

from app.shared.runtime.token_counter import ModelPricing, TokenCounter

from .contracts import ContextSection
from .errors import ContextOverflowError


class ContextTruncator:
    def __init__(self, token_counter: TokenCounter, model_pricing: ModelPricing) -> None:
        self.token_counter = token_counter
        self.model_pricing = model_pricing

    def truncate_context(
        self,
        sections: list[ContextSection],
        budget: int,
        model: str,
    ) -> list[ContextSection]:
        truncated = [replace(section) for section in sections]
        total_tokens = self.total_tokens(truncated)
        while total_tokens > budget:
            section = self._next_truncatable_section(truncated)
            if section is None:
                break
            if not self._shrink_section(section, total_tokens - budget, model):
                break
            total_tokens = self.total_tokens(truncated)
        return truncated

    def ensure_model_window(self, model: str, sections: list[ContextSection]) -> None:
        limit = self.model_pricing.get_context_window(model)
        required_sections = [
            section
            for section in sections
            if section.required and section.status not in {"not_applicable", "unused"}
        ]
        if self.total_tokens(required_sections) > limit:
            self.raise_overflow("context_window", limit, required_sections)

    def total_tokens(self, sections: list[ContextSection]) -> int:
        return sum(section.token_count for section in sections)

    def raise_overflow(
        self,
        limit_name: str,
        limit: int,
        sections: list[ContextSection],
    ) -> None:
        blocking = [section.inject_type for section in sections if section.token_count > 0]
        raise ContextOverflowError(limit_name, limit, self.total_tokens(sections), blocking)

    def _next_truncatable_section(self, sections: list[ContextSection]) -> ContextSection | None:
        candidates = [
            section
            for section in sections
            if section.content and not section.required and section.priority > 1 and section.status != "dropped"
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (item.priority, item.token_count), reverse=True)[0]

    def _shrink_section(self, section: ContextSection, overflow: int, model: str) -> bool:
        section.original_tokens = section.original_tokens or section.token_count
        if section.token_count <= section.min_tokens:
            return self._drop_section(section)
        target_tokens = section.token_count - overflow
        if target_tokens < section.min_tokens:
            return self._drop_section(section)
        truncated = self._truncate_text(section.content, target_tokens, model)
        new_tokens = self.token_counter.count(truncated, model) if truncated else 0
        if not truncated or new_tokens >= section.token_count:
            return self._drop_section(section)
        section.content = truncated
        section.token_count = new_tokens
        section.status = "truncated" if section.content else "dropped"
        return True

    def _drop_section(self, section: ContextSection) -> bool:
        section.content = ""
        section.token_count = 0
        section.status = "dropped"
        return True

    def _truncate_text(self, text: str, target_tokens: int, model: str) -> str:
        if target_tokens <= 0 or not text:
            return ""
        if self.token_counter.count(text, model) <= target_tokens:
            return text
        suffix = "\n..."
        low, high = 1, len(text)
        best = ""
        while low <= high:
            mid = (low + high) // 2
            candidate = text[:mid].rstrip() + suffix
            if self.token_counter.count(candidate, model) <= target_tokens:
                best = candidate
                low = mid + 1
            else:
                high = mid - 1
        return best
