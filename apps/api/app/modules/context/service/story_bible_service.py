from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    StoryFactConflictStatus,
    StoryFactCreateDTO,
    StoryFactCreateResolution,
    StoryFactDTO,
    StoryFactMutationAction,
    StoryFactMutationResultDTO,
    StoryFactSupersedeDTO,
    StoryFactType,
)
from .story_bible_support import (
    DEFAULT_LIMIT,
    StoryBibleMutationMixin,
    active_key_facts_statement,
    chapter_facts_statement,
    chapter_facts_to_deactivate_statement,
    duplicate_fact_statement,
    list_facts_statement,
    mark_superseded,
    story_fact_statement,
    story_source_version_statement,
    to_fact_dto,
    to_mutation_result,
)


class StoryBibleService(StoryBibleMutationMixin):
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    async def list_facts(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        fact_type: StoryFactType | None = None,
        conflict_status: StoryFactConflictStatus | None = None,
        active_only: bool = True,
        chapter_number: int | None = None,
        source_content_version_id: uuid.UUID | None = None,
        visible_at_chapter: int | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[StoryFactDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        facts = (
            await db.scalars(
                list_facts_statement(
                    project_id,
                    fact_type=fact_type,
                    conflict_status=conflict_status,
                    active_only=active_only,
                    chapter_number=chapter_number,
                    source_content_version_id=source_content_version_id,
                    visible_at_chapter=visible_at_chapter,
                    limit=limit,
                )
            )
        ).all()
        return [to_fact_dto(fact) for fact in facts]

    async def get_fact(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        fact_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> StoryFactDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        fact = await db.scalar(story_fact_statement(project_id, fact_id))
        if fact is None:
            raise NotFoundError(f"StoryFact not found: {fact_id}")
        return to_fact_dto(fact)

    async def create_fact(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: StoryFactCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> StoryFactMutationResultDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        if await db.scalar(
            story_source_version_statement(
                project_id,
                payload.source_content_version_id,
                payload.chapter_number,
            )
        ) is None:
            raise NotFoundError(f"Content version not found: {payload.source_content_version_id}")
        duplicate = await db.scalar(duplicate_fact_statement(project_id, payload))
        if duplicate is not None:
            return to_mutation_result(StoryFactMutationAction.DUPLICATE, duplicate)
        active_facts = (
            await db.scalars(
                active_key_facts_statement(project_id, payload.fact_type, payload.subject)
            )
        ).all()
        if len(active_facts) > 1:
            raise BusinessRuleError("同一 fact_type/subject 已存在未解决冲突，请先处理后再新增")
        if not active_facts and payload.resolution == StoryFactCreateResolution.SUPERSEDE:
            raise BusinessRuleError("当前没有可 supersede 的激活事实")
        new_fact = self.build_fact(project_id, payload)
        db.add(new_fact)
        action = StoryFactMutationAction.CREATED
        related_fact_ids: list[uuid.UUID] = []
        if active_facts:
            related_fact_ids = [active_facts[0].id]
            action = self.resolve_create_with_existing(active_facts[0], new_fact, payload)
        await db.commit()
        await db.refresh(new_fact)
        return to_mutation_result(action, new_fact, related_fact_ids)

    async def confirm_conflict(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        fact_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> StoryFactMutationResultDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        fact = await db.scalar(story_fact_statement(project_id, fact_id))
        if fact is None:
            raise NotFoundError(f"StoryFact not found: {fact_id}")
        if fact.conflict_with_fact_id is None:
            raise BusinessRuleError("目标事实当前没有可确认的冲突")
        counterpart = self.validate_counterpart(
            fact,
            await db.scalar(story_fact_statement(project_id, fact.conflict_with_fact_id)),
        )
        fact.conflict_status = StoryFactConflictStatus.CONFIRMED.value
        counterpart.conflict_status = StoryFactConflictStatus.CONFIRMED.value
        await db.commit()
        await db.refresh(fact)
        return to_mutation_result(
            StoryFactMutationAction.CONFIRMED_CONFLICT,
            fact,
            [counterpart.id],
        )

    async def supersede_fact(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        fact_id: uuid.UUID,
        payload: StoryFactSupersedeDTO,
        *,
        owner_id: uuid.UUID,
    ) -> StoryFactMutationResultDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        retired_fact = await db.scalar(story_fact_statement(project_id, fact_id))
        winner_fact = await db.scalar(story_fact_statement(project_id, payload.replacement_fact_id))
        if retired_fact is None:
            raise NotFoundError(f"StoryFact not found: {fact_id}")
        if winner_fact is None:
            raise NotFoundError(f"StoryFact not found: {payload.replacement_fact_id}")
        self.ensure_supersede_pair(retired_fact, winner_fact)
        mark_superseded(retired_fact, winner_fact)
        await db.commit()
        await db.refresh(winner_fact)
        return to_mutation_result(
            StoryFactMutationAction.SUPERSEDED,
            winner_fact,
            [retired_fact.id],
        )

    async def restore_version_facts(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        chapter_number: int,
        source_content_version_id: uuid.UUID,
    ) -> None:
        active_facts = (
            await db.scalars(
                chapter_facts_to_deactivate_statement(
                    project_id,
                    chapter_number,
                    source_content_version_id,
                )
            )
        ).all()
        target_facts = (
            await db.scalars(
                chapter_facts_statement(
                    project_id,
                    chapter_number,
                    source_content_version_id=source_content_version_id,
                )
            )
        ).all()
        self.restore_version_view(active_facts, target_facts)
