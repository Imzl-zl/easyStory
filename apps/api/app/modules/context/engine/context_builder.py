from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Collection

from sqlalchemy.orm import Session

from app.modules.config_registry.schemas.config_schemas import (
    ContextInjectionItem,
    ContextInjectionRule,
)
from app.shared.runtime.token_counter import ModelPricing, TokenCounter

from .contracts import ContextSection, SECTION_POLICIES, VARIABLE_NAMES
from .errors import ContextBuilderError, RequiredContextMissingError
from .source_loader import ContextSourceLoader
from .truncation import ContextTruncator


class ContextBuilder:
    """Context assembly belongs to the context module runtime layer."""

    def __init__(
        self,
        token_counter: TokenCounter,
        model_pricing: ModelPricing,
        source_loader: ContextSourceLoader,
        truncator: ContextTruncator,
    ) -> None:
        self.token_counter = token_counter
        self.model_pricing = model_pricing
        self.source_loader = source_loader
        self.truncator = truncator

    def match_patterns(
        self,
        pattern_rules: list[ContextInjectionRule],
        node_id: str,
    ) -> list[ContextInjectionItem]:
        matched: list[ContextInjectionItem] = []
        for rule in pattern_rules:
            if fnmatchcase(node_id, rule.node_pattern):
                matched.extend(rule.inject)
        return matched

    def merge_rules(
        self,
        global_rules: list[ContextInjectionItem],
        pattern_rules: list[ContextInjectionRule],
        node_id: str,
        node_rules: list[ContextInjectionItem],
    ) -> list[ContextInjectionItem]:
        merged: dict[str, ContextInjectionItem] = {}
        for item in global_rules:
            merged[item.inject_type] = item
        for item in self.match_patterns(pattern_rules, node_id):
            merged[item.inject_type] = item
        for item in node_rules:
            merged[item.inject_type] = item
        return list(merged.values())

    def build_context(
        self,
        project_id,
        injection_rules: list[ContextInjectionItem],
        db: Session,
        *,
        chapter_number: int | None = None,
        workflow_execution_id=None,
        model: str,
        budget_limit: int | None = None,
        referenced_variables: Collection[str] | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        sections = self._build_sections(
            project_id,
            injection_rules,
            db,
            chapter_number=chapter_number,
            workflow_execution_id=workflow_execution_id,
            model=model,
        )
        if referenced_variables is not None:
            sections = self._mark_unused_sections(sections, referenced_variables)
        self.ensure_model_window(model, sections)
        context_window = self.model_pricing.get_context_window(model)
        budget = min(context_window, budget_limit or context_window)
        sections = self.truncate_context(sections, budget, model)
        if self._total_tokens(sections) > budget:
            self.truncator.raise_overflow("budget_limit", budget, sections)
        return self._build_result(sections, budget, context_window)

    def truncate_context(
        self,
        sections: list[ContextSection],
        budget: int,
        model: str,
    ) -> list[ContextSection]:
        return self.truncator.truncate_context(sections, budget, model)

    def ensure_model_window(self, model: str, sections: list[ContextSection]) -> None:
        self.truncator.ensure_model_window(model, sections)

    def _build_sections(
        self,
        project_id,
        injection_rules: list[ContextInjectionItem],
        db: Session,
        *,
        chapter_number: int | None,
        workflow_execution_id,
        model: str,
    ) -> list[ContextSection]:
        return [
            self._build_section(
                project_id,
                rule,
                db,
                chapter_number=chapter_number,
                workflow_execution_id=workflow_execution_id,
                model=model,
            )
            for rule in injection_rules
        ]

    def _build_section(
        self,
        project_id,
        rule: ContextInjectionItem,
        db: Session,
        *,
        chapter_number: int | None,
        workflow_execution_id,
        model: str,
    ) -> ContextSection:
        if rule.inject_type not in VARIABLE_NAMES:
            raise ContextBuilderError(f"Unsupported inject type: {rule.inject_type}")
        content, status, metadata = self.source_loader.load_content(
            project_id,
            rule.inject_type,
            db,
            chapter_number=chapter_number,
            workflow_execution_id=workflow_execution_id,
            count=rule.count,
        )
        if status == "missing" and rule.required:
            raise RequiredContextMissingError(rule.inject_type)
        priority, min_tokens = SECTION_POLICIES[rule.inject_type]
        token_count = self.token_counter.count(content, model) if content else 0
        return ContextSection(
            inject_type=rule.inject_type,
            variable_name=VARIABLE_NAMES[rule.inject_type],
            content=content,
            priority=priority,
            min_tokens=min_tokens,
            required=rule.required,
            status=status,
            token_count=token_count,
            metadata=metadata,
        )

    def _build_result(
        self,
        sections: list[ContextSection],
        budget: int,
        context_window: int,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        total_tokens = self._total_tokens(sections)
        variables = {
            section.variable_name: section.content
            for section in sections
            if section.status != "unused"
        }
        report = {
            "total_tokens": total_tokens,
            "budget_limit": budget,
            "model_context_window": context_window,
            "sections": [section.to_report() for section in sections],
        }
        return variables, report

    def _mark_unused_sections(
        self,
        sections: list[ContextSection],
        referenced_variables: Collection[str],
    ) -> list[ContextSection]:
        referenced = set(referenced_variables)
        for section in sections:
            if section.status in {"missing", "not_applicable", "dropped"}:
                continue
            if section.variable_name in referenced:
                continue
            if section.token_count > 0:
                section.original_tokens = section.original_tokens or section.token_count
            section.content = ""
            section.token_count = 0
            section.status = "unused"
        return sections

    def _total_tokens(self, sections: list[ContextSection]) -> int:
        return self.truncator.total_tokens(sections)
