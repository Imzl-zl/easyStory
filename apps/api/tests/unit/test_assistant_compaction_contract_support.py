from app.modules.assistant.service.assistant_compaction_contract_support import (
    build_compaction_budget_exhausted_error,
    resolve_continuation_compaction_level,
    resolve_initial_prompt_compaction_level,
)


def test_resolve_initial_prompt_compaction_level_is_soft_when_recent_messages_remain() -> None:
    assert resolve_initial_prompt_compaction_level(preserved_recent_message_count=2) == "soft"


def test_resolve_initial_prompt_compaction_level_is_hard_when_recent_messages_removed() -> None:
    assert resolve_initial_prompt_compaction_level(preserved_recent_message_count=0) == "hard"


def test_resolve_continuation_compaction_level_is_soft_for_in_place_payload_trimming() -> None:
    assert (
        resolve_continuation_compaction_level(
            original_item_count=2,
            retained_item_count=2,
            dropped_content_item_count=0,
        )
        == "soft"
    )


def test_resolve_continuation_compaction_level_is_hard_for_item_or_content_item_drop() -> None:
    assert (
        resolve_continuation_compaction_level(
            original_item_count=3,
            retained_item_count=2,
            dropped_content_item_count=0,
        )
        == "hard"
    )


def test_build_compaction_budget_exhausted_error_returns_shared_terminal_error() -> None:
    error = build_compaction_budget_exhausted_error()

    assert error.code == "budget_exhausted"
    assert str(error) == "本轮上下文预算已耗尽，压缩后仍无法继续执行。"
    assert (
        resolve_continuation_compaction_level(
            original_item_count=2,
            retained_item_count=2,
            dropped_content_item_count=1,
        )
        == "hard"
    )
