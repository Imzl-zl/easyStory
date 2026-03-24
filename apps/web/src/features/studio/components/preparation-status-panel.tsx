"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api/client";
import { getProjectPreparationStatus } from "@/lib/api/projects";

type PreparationStatusPanelProps = {
  projectId: string;
};

const STEP_LABELS: Record<string, string> = {
  setting: "项目设定",
  outline: "大纲",
  opening_plan: "开篇设计",
  chapter_tasks: "章节任务",
  workflow: "工作流",
  chapter: "正文",
};

export function PreparationStatusPanel({ projectId }: PreparationStatusPanelProps) {
  const query = useQuery({
    queryKey: ["project-preparation-status", projectId],
    queryFn: () => getProjectPreparationStatus(projectId),
  });

  const rows = useMemo(() => {
    if (!query.data) {
      return [];
    }
    return [
      {
        label: "设定完整度",
        status: query.data.setting.status,
        description:
          query.data.setting.issues.length > 0
            ? query.data.setting.issues.map((issue) => issue.message).join(" / ")
            : "关键信息已满足前置创作要求。",
      },
      {
        label: "大纲",
        status: query.data.outline.step_status,
        description: describeAssetStatus(query.data.outline, "先明确故事主骨架"),
      },
      {
        label: "开篇设计",
        status: query.data.opening_plan.step_status,
        description: describeAssetStatus(query.data.opening_plan, "前 1-3 章的阶段约束"),
      },
      {
        label: "章节任务",
        status: query.data.chapter_tasks.step_status,
        description: describeTaskStatus(query.data.chapter_tasks),
      },
    ];
  }, [query.data]);

  return (
    <section className="panel-muted space-y-4 rounded-[28px] p-4">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent-ink)]">Preparation</p>
        <h2 className="font-serif text-lg font-semibold text-[var(--text-primary)]">创作准备</h2>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          当前准备链路的统一状态真值。优先看下一步提示，不再自己猜卡点。
        </p>
      </div>

      {query.isLoading ? (
        <p className="text-sm text-[var(--text-secondary)]">正在汇总创作准备状态...</p>
      ) : null}

      {query.error ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {getErrorMessage(query.error)}
        </div>
      ) : null}

      {query.data ? (
        <>
          <div className="rounded-2xl border border-[rgba(58,124,165,0.16)] bg-[rgba(58,124,165,0.06)] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">
                  Next Step
                </p>
                <p className="font-medium text-[var(--text-primary)]">
                  {STEP_LABELS[query.data.next_step] ?? query.data.next_step}
                </p>
              </div>
              <StatusBadge
                status={query.data.can_start_workflow ? "ready" : query.data.next_step}
                label={query.data.can_start_workflow ? "可启动 Workflow" : "待推进"}
              />
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
              {query.data.next_step_detail}
            </p>
            {query.data.active_workflow ? (
              <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-[var(--text-secondary)]">
                <span>当前工作流：</span>
                <span className="font-medium text-[var(--text-primary)]">
                  {query.data.active_workflow.workflow_name ?? query.data.active_workflow.workflow_id}
                </span>
                <StatusBadge status={query.data.active_workflow.status} />
              </div>
            ) : null}
          </div>

          <div className="space-y-3">
            {rows.map((row) => (
              <div
                key={row.label}
                className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.5)] px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-medium text-[var(--text-primary)]">{row.label}</p>
                  <StatusBadge status={row.status} label={formatStatusLabel(row.status)} />
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                  {row.description}
                </p>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function describeAssetStatus(
  asset: Awaited<ReturnType<typeof getProjectPreparationStatus>>["outline"],
  fallback: string,
) {
  if (asset.step_status === "not_started") {
    return fallback;
  }
  if (asset.step_status === "draft") {
    return `当前为草稿，第 ${asset.version_number ?? "?"} 版，尚未确认。`;
  }
  if (asset.step_status === "approved") {
    return `当前为已确认版本，第 ${asset.version_number ?? "?"} 版。`;
  }
  if (asset.step_status === "stale") {
    return "上游真值已变化，当前内容已失效，需要重新检查或生成。";
  }
  return "当前内容已归档。";
}

function describeTaskStatus(
  chapterTasks: Awaited<ReturnType<typeof getProjectPreparationStatus>>["chapter_tasks"],
) {
  if (chapterTasks.step_status === "not_started") {
    return "尚未生成章节任务。";
  }
  const parts = [`共 ${chapterTasks.total} 个任务`];
  if (chapterTasks.counts.pending) {
    parts.push(`${chapterTasks.counts.pending} 个未开始`);
  }
  if (chapterTasks.counts.generating) {
    parts.push(`${chapterTasks.counts.generating} 个进行中`);
  }
  if (chapterTasks.counts.completed) {
    parts.push(`${chapterTasks.counts.completed} 个已确认`);
  }
  if (chapterTasks.counts.stale) {
    parts.push(`${chapterTasks.counts.stale} 个已失效`);
  }
  if (chapterTasks.counts.failed) {
    parts.push(`${chapterTasks.counts.failed} 个失败`);
  }
  if (chapterTasks.counts.interrupted) {
    parts.push(`${chapterTasks.counts.interrupted} 个已中断`);
  }
  return parts.join(" / ");
}

function formatStatusLabel(status: string) {
  const labels: Record<string, string> = {
    ready: "Ready",
    warning: "Warning",
    blocked: "Blocked",
    not_started: "未开始",
    draft: "草稿",
    approved: "已确认",
    stale: "已失效",
    archived: "已归档",
    pending: "未开始",
    generating: "进行中",
    completed: "已确认",
    failed: "失败",
    interrupted: "已中断",
    setting: "待设定",
    outline: "待大纲",
    opening_plan: "待开篇",
    chapter_tasks: "待任务",
    workflow: "待工作流",
    chapter: "待正文",
  };
  return labels[status] ?? status;
}
