import pytest

from app.modules.assistant.service.turn.assistant_turn_preparation_runtime import (
    LangGraphAssistantTurnPreparationRuntime,
)


async def _return_async(value):
    return value


@pytest.mark.asyncio
async def test_assistant_turn_preparation_runtime_runs_stages_in_order() -> None:
    call_log: list[object] = []
    prepared_turn = object()

    runtime = LangGraphAssistantTurnPreparationRuntime(
        resolve_scope_and_normalize=lambda: _return_async(
            call_log.append("normalize") or ("project-1", "normalized-turn", "normalized-payload")
        ),
        validate_anchor=lambda project_id, normalized_payload: call_log.append(
            ("validate", project_id, normalized_payload)
        ),
        resolve_spec_and_rules=lambda project_id, normalized_payload: _return_async(
            call_log.append(("spec", project_id, normalized_payload))
            or ("spec", "rule-bundle", "system-prompt")
        ),
        build_provisional_context=lambda project_id, normalized_turn_payload, normalized_payload, spec, rule_bundle: (
            call_log.append(
                (
                    "provisional",
                    project_id,
                    normalized_turn_payload,
                    normalized_payload,
                    spec,
                    rule_bundle,
                )
            )
            or ("recovery", "injection", "provisional-turn-context")
        ),
        resolve_runtime_and_projection=lambda project_id, normalized_turn_payload, normalized_payload, spec, rule_bundle, system_prompt, provisional_turn_context, recovery_snapshot, injection_snapshot: _return_async(
            call_log.append(
                (
                    "projection",
                    project_id,
                    normalized_turn_payload,
                    normalized_payload,
                    spec,
                    rule_bundle,
                    system_prompt,
                    provisional_turn_context,
                    recovery_snapshot,
                    injection_snapshot,
                )
            )
            or (
                ("policy",),
                ("visible",),
                "run-budget",
                "llm-runtime",
                "tool-guidance",
                "prompt-projection",
                "tool-catalog-version",
            )
        ),
        build_prepared_turn=lambda state: call_log.append(("prepared", state["project_id"])) or prepared_turn,
    )

    result = await runtime.run()

    assert result is prepared_turn
    assert call_log == [
        "normalize",
        ("validate", "project-1", "normalized-payload"),
        ("spec", "project-1", "normalized-payload"),
        (
            "provisional",
            "project-1",
            "normalized-turn",
            "normalized-payload",
            "spec",
            "rule-bundle",
        ),
        (
            "projection",
            "project-1",
            "normalized-turn",
            "normalized-payload",
            "spec",
            "rule-bundle",
            "system-prompt",
            "provisional-turn-context",
            "recovery",
            "injection",
        ),
        ("prepared", "project-1"),
    ]
