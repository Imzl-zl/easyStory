"use client";

import { MetricCard } from "@/components/ui/metric-card";
import { InfoPanel } from "@/components/ui/info-panel";
import { StatusBadge } from "@/components/ui/status-badge";

import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";

type EngineWorkflowSummaryCardProps = {
  summary: WorkflowSummaryCardData;
};

export function EngineWorkflowSummaryCard({
  summary,
}: Readonly<EngineWorkflowSummaryCardProps>) {
  return (
    <InfoPanel
      className="rounded-3xl"
      description={summary.workflowIdentity}
      title="当前执行摘要"
    >
      <div className="flex flex-wrap gap-2">
        <StatusBadge status={summary.statusTone} label={summary.statusLabel} />
        <StatusBadge status={summary.modeTone} label={summary.modeLabel} />
        <StatusBadge
          status={summary.runtimeSnapshotTone}
          label={summary.runtimeSnapshotLabel}
        />
      </div>

      <InfoPanel className="rounded-2xl" tone="accent">
        <p className="text-sm leading-6 text-text-secondary">
          {summary.description}
        </p>
      </InfoPanel>

      <div className="grid gap-3 sm:grid-cols-2">
        {summary.rows.map((row) => (
          <MetricCard
            detail={row.value}
            key={row.label}
            label={row.label}
            value={row.value}
          />
        ))}
      </div>
    </InfoPanel>
  );
}
