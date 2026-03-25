"use client";

import { useQuery } from "@tanstack/react-query";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildPreparationStatusRows,
  formatPreparationNextStep,
  formatPreparationStatusLabel,
} from "@/features/project/components/preparation-status-support";
import { getErrorMessage } from "@/lib/api/client";
import { getProjectPreparationStatus } from "@/lib/api/projects";
import type { ProjectPreparationStatus } from "@/lib/api/types";

type PreparationStatusPanelProps = {
  projectId: string;
};

export function PreparationStatusPanel({ projectId }: PreparationStatusPanelProps) {
  const query = useQuery({
    queryKey: ["project-preparation-status", projectId],
    queryFn: () => getProjectPreparationStatus(projectId),
  });
  const rows = query.data ? buildPreparationStatusRows(query.data) : [];

  return (
    <section className="panel-muted space-y-4 rounded-[28px] p-4">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent-ink)]">准备状态</p>
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
          <PreparationSummaryCard preparation={query.data} />
          <PreparationRows rows={rows} />
        </>
      ) : null}
    </section>
  );
}

function PreparationSummaryCard({
  preparation,
}: Readonly<{
  preparation: ProjectPreparationStatus;
}>) {
  const badgeStatus = preparation.can_start_workflow ? "ready" : preparation.next_step;
  const badgeLabel = preparation.can_start_workflow ? "可启动 Workflow" : "待推进";
  return (
    <div className="rounded-2xl border border-[rgba(58,124,165,0.16)] bg-[rgba(58,124,165,0.06)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">
            Next Step
          </p>
          <p className="font-medium text-[var(--text-primary)]">
            {formatPreparationNextStep(preparation.next_step)}
          </p>
        </div>
        <StatusBadge status={badgeStatus} label={badgeLabel} />
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
        {preparation.next_step_detail}
      </p>
      {preparation.active_workflow ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-[var(--text-secondary)]">
          <span>当前工作流：</span>
          <span className="font-medium text-[var(--text-primary)]">
            {preparation.active_workflow.workflow_name ?? preparation.active_workflow.workflow_id}
          </span>
          <StatusBadge status={preparation.active_workflow.status} />
        </div>
      ) : null}
    </div>
  );
}

function PreparationRows({
  rows,
}: Readonly<{
  rows: ReturnType<typeof buildPreparationStatusRows>;
}>) {
  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div
          key={row.label}
          className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.5)] px-4 py-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-medium text-[var(--text-primary)]">{row.label}</p>
            <StatusBadge status={row.status} label={formatPreparationStatusLabel(row.status)} />
          </div>
          <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
            {row.description}
          </p>
        </div>
      ))}
    </div>
  );
}
