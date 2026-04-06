from app.modules.assistant.service.assistant_context_compaction_support import (
    _resolve_summary_token_budgets,
)


def test_resolve_summary_token_budgets_allows_small_compaction_candidates() -> None:
    budgets = _resolve_summary_token_budgets(36)

    assert budgets[-1] == 8
    assert min(budgets) == 8
    assert any(candidate < 24 for candidate in budgets)

