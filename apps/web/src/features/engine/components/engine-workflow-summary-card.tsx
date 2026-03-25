"use client";

import { StatusBadge } from "@/components/ui/status-badge";

import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";

type EngineWorkflowSummaryCardProps = {
  summary: WorkflowSummaryCardData;
};

export function EngineWorkflowSummaryCard({
  summary,
}: Readonly<EngineWorkflowSummaryCardProps>) {
  return (
    <section className="panel-muted space-y-4 rounded-[28px] p-4">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent-ink)]">
          Workflow Summary
        </p>
        <h2 className="font-serif text-lg font-semibold text-[var(--text-primary)]">
          当前执行摘要
        </h2>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          {summary.workflowIdentity}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusBadge status={summary.statusTone} label={summary.statusLabel} />
        <StatusBadge status={summary.modeTone} label={summary.modeLabel} />
        <StatusBadge
          status={summary.runtimeSnapshotTone}
          label={summary.runtimeSnapshotLabel}
        />
      </div>

      <div className="rounded-2xl border border-[rgba(58,124,165,0.16)] bg-[rgba(58,124,165,0.06)] p-4">
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          {summary.description}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {summary.rows.map((row) => (
          <div
            key={row.label}
            className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.5)] px-4 py-3"
          >
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">
              {row.label}
            </p>
            <p className="mt-2 font-medium text-[var(--text-primary)]">
              {row.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
