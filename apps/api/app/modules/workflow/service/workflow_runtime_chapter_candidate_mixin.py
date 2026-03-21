from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workflow.models import ChapterTask, WorkflowExecution

from .workflow_runtime_shared import ReviewCycleOutcome


class WorkflowRuntimeChapterCandidateMixin:
    async def _persist_chapter_candidate(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        task: ChapterTask,
        context_snapshot_hash: str,
        review_outcome: ReviewCycleOutcome,
    ) -> tuple[uuid.UUID | None, uuid.UUID | None, int | None]:
        if review_outcome.resolution == "skip":
            return None, None, None
        content, version = await self._save_review_candidate(
            db,
            workflow.project_id,
            task.chapter_number,
            task.title,
            review_outcome,
            context_snapshot_hash,
        )
        task.content_id = content.id
        return content.id, version.id, version.word_count

    async def _save_review_candidate(
        self,
        db: AsyncSession,
        project_id,
        chapter_number: int,
        title: str,
        review_outcome: ReviewCycleOutcome,
        context_snapshot_hash: str,
    ):
        if review_outcome.content_source == "generated":
            return await self.chapter_content_service.save_generated_draft(
                db,
                project_id,
                chapter_number,
                title=title,
                content_text=review_outcome.final_content,
                context_snapshot_hash=context_snapshot_hash,
            )
        return await self.chapter_content_service.save_auto_fix_draft(
            db,
            project_id,
            chapter_number,
            title=title,
            content_text=review_outcome.final_content,
            context_snapshot_hash=context_snapshot_hash,
            change_summary=self._auto_fix_change_summary(review_outcome),
        )

    def _auto_fix_change_summary(self, review_outcome: ReviewCycleOutcome) -> str:
        if review_outcome.resolution == "passed":
            return "自动精修后通过复审"
        return "自动精修最终候选"
