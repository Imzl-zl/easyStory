from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
import json
from typing import Any

from pydantic import ValidationError
from app.modules.project.schemas import ProjectSetting
from app.modules.template.service.guided_question_support import (
    normalize_guided_question_variable,
)
from app.modules.template.service import TemplateDetailDTO
from app.shared.runtime.errors import BusinessRuleError

from .dto import (
    ProjectIncubatorAnswerDTO,
    ProjectIncubatorAppliedAnswerDTO,
    ProjectIncubatorQuestionDTO,
    ProjectIncubatorTemplateDTO,
    ProjectIncubatorUnmappedAnswerDTO,
    SettingCompletenessResultDTO,
)

PROJECT_SETTING_CONVERSATION_SKILL_ID = "skill.project_setting.conversation_extract"

FOLLOW_UP_QUESTION_BY_FIELD = {
    "genre": "你想写什么题材或类型？",
    "protagonist.identity": "主角当前是什么身份，或者一开始处在什么处境？",
    "protagonist.goal": "主角最核心、最想达成的目标是什么？",
    "core_conflict": "这个故事最核心的冲突或主线矛盾是什么？",
    "world_setting": "故事发生在什么时代、世界或环境里？有哪些关键规则或地点？",
    "tone": "你希望整体基调或文风更偏什么感觉？",
    "scale": "这本书大概准备写多少字，或者规划多少章？",
}


@dataclass(frozen=True)
class _AnswerRule:
    field_path: str
    parser: Callable[[str], str | int | list[str]]


def build_incubator_template_snapshot(
    template: TemplateDetailDTO,
) -> ProjectIncubatorTemplateDTO:
    return ProjectIncubatorTemplateDTO(
        id=template.id,
        name=template.name,
        description=template.description,
        genre=template.genre,
        workflow_id=template.workflow_id,
        guided_questions=[
            ProjectIncubatorQuestionDTO(
                question=question.question,
                variable=question.variable,
            )
            for question in template.guided_questions
        ],
    )


def ensure_answers_match_template(
    template: TemplateDetailDTO,
    answers: Sequence[ProjectIncubatorAnswerDTO],
) -> None:
    declared_variables = {
        normalize_guided_question_variable(question.variable)
        for question in template.guided_questions
    }
    seen_variables: set[str] = set()
    for answer in answers:
        variable = normalize_guided_question_variable(answer.variable)
        if variable in seen_variables:
            raise BusinessRuleError(f"模板引导变量重复提交: {variable}")
        seen_variables.add(variable)
        if variable not in declared_variables:
            raise BusinessRuleError(f"模板未声明引导变量: {variable}")
        if not answer.value.strip():
            raise BusinessRuleError(f"模板引导变量值不能为空: {variable}")


def build_project_setting_draft(
    template: TemplateDetailDTO,
    answers: Sequence[ProjectIncubatorAnswerDTO],
) -> tuple[
    ProjectSetting,
    list[ProjectIncubatorAppliedAnswerDTO],
    list[ProjectIncubatorUnmappedAnswerDTO],
]:
    draft_payload: dict[str, Any] = {}
    if template.genre:
        _set_nested_value(draft_payload, "genre", template.genre.strip())

    applied_answers: list[ProjectIncubatorAppliedAnswerDTO] = []
    unmapped_answers: list[ProjectIncubatorUnmappedAnswerDTO] = []
    for answer in answers:
        normalized_value = answer.value.strip()
        variable = normalize_guided_question_variable(answer.variable)
        rule = ANSWER_RULES.get(variable)
        if rule is None:
            unmapped_answers.append(
                ProjectIncubatorUnmappedAnswerDTO(
                    variable=variable,
                    value=normalized_value,
                    reason="unsupported_variable",
                )
            )
            continue
        parsed_value = rule.parser(normalized_value)
        _set_nested_value(draft_payload, rule.field_path, parsed_value)
        applied_answers.append(
            ProjectIncubatorAppliedAnswerDTO(
                variable=variable,
                field_path=rule.field_path,
                value=parsed_value,
            )
        )
    return ProjectSetting.model_validate(draft_payload), applied_answers, unmapped_answers


def parse_project_setting_output(raw_content: Any) -> ProjectSetting:
    payload = _parse_json(raw_content)
    if not isinstance(payload, dict):
        raise BusinessRuleError("自由设定提取必须返回 JSON 对象")
    try:
        return ProjectSetting.model_validate(payload)
    except ValidationError as exc:
        raise BusinessRuleError(
            f"自由设定提取结果不符合 ProjectSetting schema: {exc}"
        ) from exc


def build_setting_follow_up_questions(
    result: SettingCompletenessResultDTO,
) -> list[str]:
    questions: list[str] = []
    for issue in result.issues:
        question = FOLLOW_UP_QUESTION_BY_FIELD.get(issue.field, f"请补充：{issue.message}")
        if question not in questions:
            questions.append(question)
    return questions


def normalize_conversation_text(raw_text: str) -> str:
    normalized = raw_text.strip()
    if not normalized:
        raise BusinessRuleError("conversation_text cannot be blank")
    return normalized


def normalize_requested_provider(raw_provider: str) -> str:
    normalized = raw_provider.strip().lower()
    if not normalized:
        raise BusinessRuleError("provider cannot be blank")
    return normalized


def normalize_requested_model_name(raw_model_name: str | None) -> str | None:
    if raw_model_name is None:
        return None
    normalized = raw_model_name.strip()
    if not normalized:
        raise BusinessRuleError("model_name cannot be blank")
    return normalized


def _parse_json(raw_content: Any) -> Any:
    if isinstance(raw_content, dict | list):
        return raw_content
    if not isinstance(raw_content, str):
        raise BusinessRuleError("LLM 输出必须是 JSON 字符串或对象")
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise BusinessRuleError("LLM 输出不是合法 JSON") from exc


def _set_nested_value(payload: dict[str, Any], field_path: str, value: Any) -> None:
    segments = field_path.split(".")
    current = payload
    for segment in segments[:-1]:
        current = current.setdefault(segment, {})
    current[segments[-1]] = value


def _parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise BusinessRuleError(f"数值字段必须是整数: {value}") from exc
    if parsed <= 0:
        raise BusinessRuleError(f"数值字段必须大于 0: {value}")
    return parsed


def _parse_locations(value: str) -> list[str]:
    items = [item.strip() for item in _split_location_tokens(value) if item.strip()]
    if not items:
        raise BusinessRuleError("key_locations 不能为空")
    return items


def _split_location_tokens(value: str) -> Iterable[str]:
    normalized = value.replace("、", ",").replace("\n", ",")
    return normalized.split(",")


ANSWER_RULES = {
    "genre": _AnswerRule("genre", lambda value: value),
    "sub_genre": _AnswerRule("sub_genre", lambda value: value),
    "target_readers": _AnswerRule("target_readers", lambda value: value),
    "tone": _AnswerRule("tone", lambda value: value),
    "conflict": _AnswerRule("core_conflict", lambda value: value),
    "core_conflict": _AnswerRule("core_conflict", lambda value: value),
    "plot_direction": _AnswerRule("plot_direction", lambda value: value),
    "special_requirements": _AnswerRule("special_requirements", lambda value: value),
    "protagonist": _AnswerRule("protagonist.identity", lambda value: value),
    "protagonist_name": _AnswerRule("protagonist.name", lambda value: value),
    "protagonist_identity": _AnswerRule("protagonist.identity", lambda value: value),
    "protagonist_goal": _AnswerRule("protagonist.goal", lambda value: value),
    "protagonist_background": _AnswerRule("protagonist.background", lambda value: value),
    "protagonist_personality": _AnswerRule("protagonist.personality", lambda value: value),
    "protagonist_initial_situation": _AnswerRule(
        "protagonist.initial_situation",
        lambda value: value,
    ),
    "world_setting": _AnswerRule("world_setting.era_baseline", lambda value: value),
    "world_name": _AnswerRule("world_setting.name", lambda value: value),
    "world_rules": _AnswerRule("world_setting.world_rules", lambda value: value),
    "power_system": _AnswerRule("world_setting.power_system", lambda value: value),
    "target_words": _AnswerRule("scale.target_words", _parse_positive_int),
    "target_chapters": _AnswerRule("scale.target_chapters", _parse_positive_int),
    "pacing": _AnswerRule("scale.pacing", lambda value: value),
    "key_locations": _AnswerRule("world_setting.key_locations", _parse_locations),
}
