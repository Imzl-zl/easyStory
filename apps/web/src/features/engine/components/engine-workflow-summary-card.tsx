"use client";

import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";

type EngineWorkflowSummaryCardProps = {
  summary: WorkflowSummaryCardData;
};

export function EngineWorkflowSummaryCard({
  summary,
}: Readonly<EngineWorkflowSummaryCardProps>) {
  return (
    <div className="rounded p-4" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>
            执行摘要
          </span>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded"
            style={{
              background:
                summary.statusTone === "completed"
                  ? "var(--accent-success-soft)"
                  : summary.statusTone === "failed"
                    ? "var(--accent-danger-soft)"
                    : summary.statusTone === "running"
                      ? "var(--accent-primary-soft)"
                      : "var(--line-soft)",
              color:
                summary.statusTone === "completed"
                  ? "var(--accent-success)"
                  : summary.statusTone === "failed"
                    ? "var(--accent-danger)"
                    : summary.statusTone === "running"
                      ? "var(--accent-primary)"
                      : "var(--text-secondary)",
            }}
          >
            {summary.statusLabel}
          </span>
        </div>
        <p className="text-[12px]" style={{ color: "var(--text-primary)" }}>
          {summary.description}
        </p>
        <div className="grid grid-cols-2 gap-2">
          {summary.rows.map((row) => (
            <div
              key={row.label}
              className="rounded p-2.5"
              style={{ background: "var(--bg-canvas)" }}
            >
              <p className="text-[10px] mb-0.5" style={{ color: "var(--text-tertiary)" }}>
                {row.label}
              </p>
              <p className="text-[12px] font-medium" style={{ color: "var(--text-secondary)" }}>
                {row.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
