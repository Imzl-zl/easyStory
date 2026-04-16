"use client";

import { useQuery } from "@tanstack/react-query";

import { InfoPanel } from "@/components/ui/info-panel";
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
    <InfoPanel
      className="rounded-3xl"
      description="查看当前准备进度和下一步。"
      title="创作准备"
    >
      {query.isLoading ? (
        <p className="text-sm text-text-secondary">正在汇总创作准备状态...</p>
      ) : null}

      {query.error ? (
        <InfoPanel tone="danger" className="rounded-2xl">
          <p className="text-sm text-accent-danger">{getErrorMessage(query.error)}</p>
        </InfoPanel>
      ) : null}

      {query.data ? (
        <>
          <PreparationSummaryCard preparation={query.data} />
          <PreparationRows rows={rows} />
        </>
      ) : null}
    </InfoPanel>
  );
}

function PreparationSummaryCard({
  preparation,
}: Readonly<{
  preparation: ProjectPreparationStatus;
}>) {
  const badgeStatus = preparation.can_start_workflow ? "ready" : preparation.next_step;
  const badgeLabel = preparation.can_start_workflow ? "可启动工作流" : "待推进";
  return (
    <InfoPanel tone="accent" className="rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.16em] text-text-secondary">
            下一步
          </p>
          <p className="font-medium text-text-primary">
            {formatPreparationNextStep(preparation.next_step)}
          </p>
        </div>
        <StatusBadge status={badgeStatus} label={badgeLabel} />
      </div>
      <p className="mt-3 text-sm leading-6 text-text-secondary">
        {preparation.next_step_detail}
      </p>
      {preparation.active_workflow ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-text-secondary">
          <span>当前工作流：</span>
          <span className="font-medium text-text-primary">
            {preparation.active_workflow.workflow_name ?? preparation.active_workflow.workflow_id}
          </span>
          <StatusBadge status={preparation.active_workflow.status} />
        </div>
      ) : null}
    </InfoPanel>
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
        <InfoPanel key={row.label} className="rounded-2xl px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-medium text-text-primary">{row.label}</p>
            <StatusBadge status={row.status} label={formatPreparationStatusLabel(row.status)} />
          </div>
          <p className="mt-2 text-sm leading-6 text-text-secondary">
            {row.description}
          </p>
        </InfoPanel>
      ))}
    </div>
  );
}
