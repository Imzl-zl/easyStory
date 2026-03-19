import pytest
from jinja2.exceptions import SecurityError, UndefinedError

from app.shared.runtime.template_renderer import SkillTemplateRenderer


def test_render_basic() -> None:
    renderer = SkillTemplateRenderer()

    result = renderer.render("Hello {{ name }}", {"name": "World"})

    assert result == "Hello World"


def test_strict_undefined_raises() -> None:
    renderer = SkillTemplateRenderer()

    with pytest.raises(UndefinedError):
        renderer.render("{{ missing_var }}", {})


def test_sandbox_blocks_dangerous_attribute_access() -> None:
    renderer = SkillTemplateRenderer()

    with pytest.raises(SecurityError):
        renderer.render("{{ ''.__class__ }}", {})


def test_render_rejects_forbidden_template_feature() -> None:
    renderer = SkillTemplateRenderer()

    with pytest.raises(SecurityError, match="macro"):
        renderer.render("{% macro greet() %}x{% endmacro %}", {})


def test_validate_finds_missing_vars_and_forbidden_features() -> None:
    renderer = SkillTemplateRenderer()

    errors = renderer.validate(
        "{% include 'x' %} {{ a }} {{ b }}",
        {"a"},
    )

    assert "Forbidden template feature: include" in errors
    assert "Undeclared variable: b" in errors


def test_validate_reports_template_syntax_error() -> None:
    renderer = SkillTemplateRenderer()

    errors = renderer.validate("{{ name ", {"name"})

    assert errors
    assert errors[0].startswith("Template syntax error:")


def test_referenced_variables_reports_runtime_inputs() -> None:
    renderer = SkillTemplateRenderer()

    referenced = renderer.referenced_variables(
        "{% if previous_content %}{{ previous_content }}{% endif %} {{ chapter_task }}"
    )

    assert referenced == {"previous_content", "chapter_task"}
