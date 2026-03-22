from __future__ import annotations

import uuid

from sqlalchemy import select

from app.modules.content.models import Content, ContentVersion
from app.modules.context.models import StoryFact
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .dto import (
    StoryFactConflictStatus,
    StoryFactCreateDTO,
    StoryFactCreateResolution,
    StoryFactDTO,
    StoryFactMutationAction,
    StoryFactMutationResultDTO,
    StoryFactType,
)

DEFAULT_LIMIT = 200


def list_facts_statement(
    project_id: uuid.UUID,
    *,
    fact_type: StoryFactType | None,
    conflict_status: StoryFactConflictStatus | None,
    active_only: bool,
    chapter_number: int | None,
    source_content_version_id: uuid.UUID | None,
    visible_at_chapter: int | None,
    limit: int,
):
    statement = select(StoryFact).where(StoryFact.project_id == project_id)
    if fact_type is not None:
        statement = statement.where(StoryFact.fact_type == fact_type.value)
    if conflict_status is not None:
        statement = statement.where(StoryFact.conflict_status == conflict_status.value)
    if active_only:
        statement = statement.where(StoryFact.is_active.is_(True))
    if chapter_number is not None:
        statement = statement.where(StoryFact.chapter_number == chapter_number)
    if source_content_version_id is not None:
        statement = statement.where(StoryFact.source_content_version_id == source_content_version_id)
    if visible_at_chapter is not None:
        statement = statement.where(StoryFact.chapter_number <= visible_at_chapter)
    return statement.order_by(
        StoryFact.chapter_number.asc(),
        StoryFact.fact_type.asc(),
        StoryFact.subject.asc(),
        StoryFact.created_at.asc(),
        StoryFact.id.asc(),
    ).limit(limit)


def story_source_version_statement(
    project_id: uuid.UUID,
    source_content_version_id: uuid.UUID,
    chapter_number: int,
):
    return (
        select(ContentVersion)
        .join(Content, ContentVersion.content_id == Content.id)
        .where(
            ContentVersion.id == source_content_version_id,
            Content.project_id == project_id,
            Content.content_type == "chapter",
            Content.chapter_number == chapter_number,
        )
    )


def story_fact_statement(project_id: uuid.UUID, fact_id: uuid.UUID):
    return select(StoryFact).where(
        StoryFact.id == fact_id,
        StoryFact.project_id == project_id,
    )


def active_key_facts_statement(
    project_id: uuid.UUID,
    fact_type: StoryFactType,
    subject: str,
):
    return (
        select(StoryFact)
        .where(
            StoryFact.project_id == project_id,
            StoryFact.fact_type == fact_type.value,
            StoryFact.subject == subject,
            StoryFact.is_active.is_(True),
            StoryFact.superseded_by.is_(None),
        )
        .order_by(StoryFact.created_at.asc(), StoryFact.id.asc())
    )


def duplicate_fact_statement(
    project_id: uuid.UUID,
    payload: StoryFactCreateDTO,
):
    return select(StoryFact).where(
        StoryFact.project_id == project_id,
        StoryFact.source_content_version_id == payload.source_content_version_id,
        StoryFact.fact_type == payload.fact_type.value,
        StoryFact.subject == payload.subject,
        StoryFact.content == payload.content,
        StoryFact.is_active.is_(True),
        StoryFact.superseded_by.is_(None),
    )


def chapter_facts_statement(
    project_id: uuid.UUID,
    chapter_number: int,
    *,
    source_content_version_id: uuid.UUID | None = None,
    active_only: bool = False,
):
    statement = select(StoryFact).where(
        StoryFact.project_id == project_id,
        StoryFact.chapter_number == chapter_number,
    )
    if source_content_version_id is not None:
        statement = statement.where(
            StoryFact.source_content_version_id == source_content_version_id
        )
    if active_only:
        statement = statement.where(StoryFact.is_active.is_(True))
    return statement


def chapter_facts_to_deactivate_statement(
    project_id: uuid.UUID,
    chapter_number: int,
    source_content_version_id: uuid.UUID,
):
    return chapter_facts_statement(project_id, chapter_number, active_only=True).where(
        StoryFact.source_content_version_id != source_content_version_id
    )


def to_fact_dto(fact: StoryFact) -> StoryFactDTO:
    return StoryFactDTO.model_validate(fact, from_attributes=True)


def to_mutation_result(
    action: StoryFactMutationAction,
    fact: StoryFact,
    related_fact_ids: list[uuid.UUID] | None = None,
) -> StoryFactMutationResultDTO:
    return StoryFactMutationResultDTO(
        action=action,
        fact=to_fact_dto(fact),
        related_fact_ids=related_fact_ids or [],
    )


def mark_potential_conflict(left: StoryFact, right: StoryFact) -> None:
    left.conflict_status = StoryFactConflictStatus.POTENTIAL.value
    left.conflict_with_fact_id = right.id
    right.conflict_status = StoryFactConflictStatus.POTENTIAL.value
    right.conflict_with_fact_id = left.id


def mark_superseded(retired: StoryFact, winner: StoryFact) -> None:
    retired.is_active = False
    retired.superseded_by = winner.id
    retired.conflict_status = StoryFactConflictStatus.NONE.value
    retired.conflict_with_fact_id = None
    winner.is_active = True
    winner.superseded_by = None
    winner.conflict_status = StoryFactConflictStatus.NONE.value
    if winner.conflict_with_fact_id == retired.id:
        winner.conflict_with_fact_id = None


class StoryBibleMutationMixin:
    def build_fact(
        self,
        project_id: uuid.UUID,
        payload: StoryFactCreateDTO,
    ) -> StoryFact:
        return StoryFact(
            id=uuid.uuid4(),
            project_id=project_id,
            chapter_number=payload.chapter_number,
            source_content_version_id=payload.source_content_version_id,
            fact_type=payload.fact_type.value,
            subject=payload.subject,
            content=payload.content,
            is_active=True,
            conflict_status=StoryFactConflictStatus.NONE.value,
        )

    def resolve_create_with_existing(
        self,
        existing_fact: StoryFact,
        new_fact: StoryFact,
        payload: StoryFactCreateDTO,
    ) -> StoryFactMutationAction:
        if existing_fact.source_content_version_id == payload.source_content_version_id:
            mark_superseded(existing_fact, new_fact)
            return StoryFactMutationAction.SUPERSEDED
        if payload.resolution == StoryFactCreateResolution.SUPERSEDE:
            if payload.supersede_fact_id != existing_fact.id:
                raise BusinessRuleError("supersede_fact_id 与当前激活事实不一致")
            mark_superseded(existing_fact, new_fact)
            return StoryFactMutationAction.SUPERSEDED
        mark_potential_conflict(existing_fact, new_fact)
        return StoryFactMutationAction.POTENTIAL_CONFLICT

    def ensure_supersede_pair(
        self,
        retired_fact: StoryFact,
        winner_fact: StoryFact,
    ) -> None:
        if retired_fact.id == winner_fact.id:
            raise BusinessRuleError("不能用同一条事实 supersede 自己")
        if retired_fact.fact_type != winner_fact.fact_type:
            raise BusinessRuleError("supersede 仅允许同 fact_type 的事实之间执行")
        if retired_fact.subject != winner_fact.subject:
            raise BusinessRuleError("supersede 仅允许同 subject 的事实之间执行")
        if retired_fact.conflict_with_fact_id not in (None, winner_fact.id):
            raise BusinessRuleError("目标旧事实存在其他未解决冲突，不能直接 supersede")
        if winner_fact.conflict_with_fact_id not in (None, retired_fact.id):
            raise BusinessRuleError("replacement_fact 存在其他未解决冲突，不能直接 supersede")

    def validate_counterpart(
        self,
        fact: StoryFact,
        counterpart: StoryFact | None,
    ) -> StoryFact:
        if counterpart is None:
            raise ConfigurationError(
                f"StoryFact conflict target missing: {fact.conflict_with_fact_id}"
            )
        if fact.fact_type != counterpart.fact_type or fact.subject != counterpart.subject:
            raise ConfigurationError(f"StoryFact conflict pair mismatch: {fact.id}")
        return counterpart

    def restore_version_view(
        self,
        active_facts: list[StoryFact],
        target_version_facts: list[StoryFact],
    ) -> None:
        for fact in active_facts:
            fact.is_active = False
        for fact in target_version_facts:
            fact.is_active = True
            fact.superseded_by = None
