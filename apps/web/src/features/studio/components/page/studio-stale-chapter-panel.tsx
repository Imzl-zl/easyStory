"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildEngineTaskHref,
  getEngineTaskCtaLabel,
  resolvePreparationWorkflowId,
} from "@/features/studio/components/page/studio-navigation-support";
import { getProjectPreparationStatus } from "@/lib/api/projects";
import type { ChapterSummary } from "@/lib/api/types";

type StudioStaleChapterPanelProps = {
  projectId: string;
  staleChapters: ChapterSummary[];
  onFocusChapter: (chapterNumber: number) => void;
};

export function StudioStaleChapterPanel({
  projectId,
  staleChapters,
  onFocusChapter,
}: StudioStaleChapterPanelProps) {
  const firstStaleChapter = staleChapters[0];
  const preparationQuery = useQuery({
    queryKey: ["project-preparation-status", projectId],
    queryFn: () => getProjectPreparationStatus(projectId),
  });
  const workflowId = resolvePreparationWorkflowId(preparationQuery.data);
  const isWorkflowPending = preparationQuery.isLoading && workflowId === null;

  return (
    <section className="panel-muted space-y-4 rounded-3xl p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-sm text-text-secondary">失效章节待处理</p>
          <p className="text-sm leading-6 text-text-secondary">
            {staleChapters.length} 个章节基于旧上下文，建议逐章复核。
          </p>
        </div>
        <StatusBadge status="stale" label={`${staleChapters.length} 章待复核`} />
      </div>

      <div className="flex flex-wrap gap-2">
        <button className="ink-button-secondary" onClick={() => onFocusChapter(firstStaleChapter.chapter_number)}>
          优先处理第 {firstStaleChapter.chapter_number} 章
        </button>
        {isWorkflowPending ? (
          <button className="ink-button-secondary" disabled>
            正在解析 workflow...
          </button>
        ) : (
          <Link
            className="ink-button-secondary"
            href={buildEngineTaskHref(projectId, workflowId)}
          >
            {getEngineTaskCtaLabel(workflowId)}
          </Link>
        )}
      </div>
      {!workflowId && !isWorkflowPending ? (
        <p className="text-xs leading-5 text-text-secondary">
          进入 Engine 载入 workflow 后再决定是否重建章节计划。
        </p>
      ) : null}
    </section>
  );
}
