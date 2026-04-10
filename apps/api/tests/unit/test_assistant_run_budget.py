from app.modules.assistant.service.assistant_run_budget import (
    enrich_assistant_run_budget_with_input_window,
)


def test_enrich_assistant_run_budget_keeps_small_context_windows_unchanged_without_output_limit() -> None:
    budget = enrich_assistant_run_budget_with_input_window(
        None,
        context_window_tokens=4096,
        max_output_tokens=None,
    )

    assert budget is not None
    assert budget.max_input_tokens == 4096


def test_enrich_assistant_run_budget_reserves_output_tokens_for_large_context_windows() -> None:
    budget = enrich_assistant_run_budget_with_input_window(
        None,
        context_window_tokens=32000,
        max_output_tokens=None,
    )

    assert budget is not None
    assert budget.max_input_tokens == 23808
