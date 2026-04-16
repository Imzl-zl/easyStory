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

type ChapterStaleNoticeProps = {
  chapterNumber: number;
  projectId: string;
};

export function ChapterStaleNotice({ chapterNumber, projectId }: ChapterStaleNoticeProps) {
  const preparationQuery = useQuery({
    queryKey: ["project-preparation-status", projectId],
    queryFn: () => getProjectPreparationStatus(projectId),
  });
  const workflowId = resolvePreparationWorkflowId(preparationQuery.data);
  const isWorkflowPending = preparationQuery.isLoading && workflowId === null;

  return (
    <section className="callout-warning p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-sm font-medium text-text-primary">
            第 {chapterNumber} 章基于旧上下文，当前处于 stale 状态
          </p>
          <p className="text-sm leading-6 text-text-secondary">
            如果你已复核这章正文仍然成立，可以直接点击上方“确认”恢复为 approved；如果这章也需要跟随上游变化重写，先去 Engine 处理章节任务更稳妥。
          </p>
        </div>
        <StatusBadge status="stale" label="待复核" />
      </div>

      <div className="mt-4">
        {isWorkflowPending ? (
          <button className="ink-button-secondary" disabled>
            正在解析 workflow...
          </button>
        ) : (
          <Link className="ink-button-secondary" href={buildEngineTaskHref(projectId, workflowId)}>
            {getEngineTaskCtaLabel(workflowId)}
          </Link>
        )}
      </div>
      {!workflowId && !isWorkflowPending ? (
        <p className="mt-3 text-xs leading-5 text-text-secondary">
          当前还没有可直接定位的 workflow，进入 Engine 后先载入当前 workflow，再决定是否重建任务。
        </p>
      ) : null}
    </section>
  );
}
