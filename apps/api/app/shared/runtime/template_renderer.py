from __future__ import annotations

from typing import Any, Collection

from jinja2 import StrictUndefined, meta, nodes
from jinja2.exceptions import SecurityError, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

FORBIDDEN_TEMPLATE_FEATURES = {
    nodes.Macro: "macro",
    nodes.Import: "import",
    nodes.FromImport: "from import",
    nodes.Include: "include",
    nodes.Extends: "extends",
}


class SkillTemplateRenderer:
    def __init__(self) -> None:
        self.env = SandboxedEnvironment(undefined=StrictUndefined)
        self.env.filters.update(
            {
                "truncate": self._safe_truncate,
                "default": self._safe_default,
            }
        )

    def render(self, template_str: str, variables: dict[str, Any]) -> str:
        ast = self.env.parse(template_str)
        self._ensure_supported_template(ast)
        template = self.env.from_string(template_str)
        return template.render(**variables)

    def referenced_variables(self, template_str: str) -> set[str]:
        ast = self.env.parse(template_str)
        self._ensure_supported_template(ast)
        return self._collect_referenced_variables(ast)

    def validate(
        self,
        template_str: str,
        declared_variables: Collection[str],
    ) -> list[str]:
        try:
            ast = self.env.parse(template_str)
        except TemplateSyntaxError as exc:
            return [f"Template syntax error: {exc.message}"]

        errors = self._collect_forbidden_feature_errors(ast)
        referenced = self._collect_referenced_variables(ast)
        missing = sorted(referenced - set(declared_variables))
        errors.extend(f"Undeclared variable: {name}" for name in missing)
        return errors

    def _ensure_supported_template(self, ast: nodes.Template) -> None:
        errors = self._collect_forbidden_feature_errors(ast)
        if errors:
            raise SecurityError("; ".join(errors))

    def _collect_forbidden_feature_errors(
        self,
        ast: nodes.Template,
    ) -> list[str]:
        errors: list[str] = []
        for node_type, feature_name in FORBIDDEN_TEMPLATE_FEATURES.items():
            if any(ast.find_all(node_type)):
                errors.append(f"Forbidden template feature: {feature_name}")
        return errors

    @staticmethod
    def _collect_referenced_variables(ast: nodes.Template) -> set[str]:
        return set(meta.find_undeclared_variables(ast))

    @staticmethod
    def _safe_truncate(value: Any, length: int = 100) -> str:
        text = str(value)
        if len(text) <= length:
            return text
        return text[:length] + "..."

    @staticmethod
    def _safe_default(
        value: Any,
        default_value: Any = "",
        use_falsey: bool = True,
    ) -> Any:
        if use_falsey:
            return value if value else default_value
        return value if value is not None else default_value
