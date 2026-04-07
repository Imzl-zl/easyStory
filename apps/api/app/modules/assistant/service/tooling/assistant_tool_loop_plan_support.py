from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..assistant_run_budget import AssistantRunBudget
from ..assistant_runtime_terminal import AssistantRuntimeTerminalError
from .assistant_tool_runtime_dto import AssistantToolDescriptor, AssistantToolPolicyDecision


@dataclass(frozen=True)
class AssistantToolLoopPlannedToolCall:
    tool_call: dict[str, Any]
    descriptor: AssistantToolDescriptor
    tool_policy_decision: AssistantToolPolicyDecision | None
    step_index: int


def _build_policy_decision_by_name(
    policy_decisions: tuple[AssistantToolPolicyDecision, ...],
) -> dict[str, AssistantToolPolicyDecision]:
    return {
        item.descriptor.name: item
        for item in policy_decisions
    }


def _plan_tool_cycle_calls(
    *,
    tool_calls: list[dict[str, Any]],
    policy_decision_by_name: dict[str, AssistantToolPolicyDecision],
    require_tool_descriptor: Callable[[str], AssistantToolDescriptor],
    run_budget: AssistantRunBudget,
    step_index: int,
) -> tuple[tuple[AssistantToolLoopPlannedToolCall, ...], int]:
    planned_calls: list[AssistantToolLoopPlannedToolCall] = []
    next_step_index = step_index
    for tool_call in tool_calls:
        tool_name = str(tool_call["tool_name"])
        tool_policy_decision = _require_visible_tool_policy_decision(
            tool_name=tool_name,
            policy_decision_by_name=policy_decision_by_name,
            require_tool_descriptor=require_tool_descriptor,
        )
        descriptor = tool_policy_decision.descriptor
        next_step_index = _advance_tool_step_index(
            run_budget=run_budget,
            step_index=next_step_index,
        )
        planned_calls.append(
            AssistantToolLoopPlannedToolCall(
                tool_call=tool_call,
                descriptor=descriptor,
                tool_policy_decision=tool_policy_decision,
                step_index=next_step_index,
            )
        )
    return tuple(planned_calls), next_step_index


def _require_visible_tool_policy_decision(
    *,
    tool_name: str,
    policy_decision_by_name: dict[str, AssistantToolPolicyDecision],
    require_tool_descriptor: Callable[[str], AssistantToolDescriptor],
) -> AssistantToolPolicyDecision:
    tool_policy_decision = policy_decision_by_name.get(tool_name)
    if tool_policy_decision is None:
        require_tool_descriptor(tool_name)
        raise AssistantRuntimeTerminalError(
            code="tool_not_exposed",
            message=f"模型请求了当前 run 未暴露的工具：{tool_name}。",
        )
    if tool_policy_decision.visibility != "visible":
        raise AssistantRuntimeTerminalError(
            code="tool_not_exposed",
            message=_build_hidden_tool_message(tool_policy_decision),
        )
    return tool_policy_decision


def _build_hidden_tool_message(tool_policy_decision: AssistantToolPolicyDecision) -> str:
    tool_name = tool_policy_decision.descriptor.name
    hidden_reason = tool_policy_decision.hidden_reason
    if hidden_reason == "write_grant_unavailable":
        return f"模型请求了当前 run 未获写入授权的工具：{tool_name}。"
    if hidden_reason == "unsupported_approval_mode":
        return f"模型请求了当前运行时尚不支持审批模式的工具：{tool_name}。"
    if hidden_reason == "not_in_project_scope":
        return f"模型请求了当前项目范围外的工具：{tool_name}。"
    return f"模型请求了当前 run 未暴露的工具：{tool_name}。"


def _advance_tool_step_index(
    *,
    run_budget: AssistantRunBudget,
    step_index: int,
) -> int:
    if run_budget.max_steps is not None and step_index >= run_budget.max_steps:
        raise AssistantRuntimeTerminalError(
            code="budget_exhausted",
            message="本轮工具步骤预算已耗尽，已停止继续执行。",
        )
    return step_index + 1
