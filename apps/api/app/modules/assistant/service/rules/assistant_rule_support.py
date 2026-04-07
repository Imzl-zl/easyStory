from __future__ import annotations

from app.shared.runtime.errors import ConfigurationError


def normalize_rule_content(content: str) -> str:
    return content.strip()


def normalize_rule_include_paths(raw_include: object) -> tuple[str, ...]:
    if raw_include is None:
        return ()
    if not isinstance(raw_include, list):
        raise ConfigurationError("Assistant rule file include must be a YAML string list")
    include_paths: list[str] = []
    for item in raw_include:
        if not isinstance(item, str) or not item.strip():
            raise ConfigurationError(
                "Assistant rule file include entries must be non-empty strings"
            )
        include_paths.append(item.strip())
    return tuple(include_paths)


def assemble_rule_runtime_content(*sections: str) -> str:
    normalized_sections = [normalize_rule_content(section) for section in sections if section.strip()]
    return "\n\n".join(normalized_sections)


def build_assistant_system_prompt(
    base_system_prompt: str | None,
    *,
    user_content: str | None,
    project_content: str | None,
) -> str | None:
    sections: list[str] = []
    if base_system_prompt and base_system_prompt.strip():
        sections.append(base_system_prompt.strip())
    extra_rules = _build_rule_sections(user_content=user_content, project_content=project_content)
    if extra_rules:
        sections.append(
            "请额外遵守以下长期规则。若规则冲突，以更具体、位置更靠后的规则为准。"
        )
        sections.extend(extra_rules)
    if not sections:
        return None
    return "\n\n".join(sections)


def _build_rule_sections(*, user_content: str | None, project_content: str | None) -> list[str]:
    sections: list[str] = []
    if user_content:
        sections.append(f"【用户长期规则】\n{user_content}")
    if project_content:
        sections.append(f"【当前项目规则】\n{project_content}")
    return sections
