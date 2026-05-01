"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { PageEntrance } from "@/components/ui/page-entrance";
import { EmptyState } from "@/components/ui/empty-state";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";

import type { EngineWorkflowControl, WorkflowAction } from "./engine-workflow-controls";
import { EngineWorkflowDebugPanel } from "./engine-workflow-debug-panel";
import { EngineWorkflowStatusCallout } from "./engine-workflow-status-callout";
import { EngineWorkflowSummaryCard } from "./engine-workflow-summary-card";
import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";
import type { EngineTabKey } from "./engine-workflow-status-support";
import type { WorkflowExecution } from "@/lib/api/types";

export type EnginePageBanner = {
  id: string;
  message: string;
  tone: "danger" | "warning";
};

type EnginePageShellProps = {
  banners: EnginePageBanner[];
  detailPanel: ReactNode;
  hasWorkflow: boolean;
  isActionPending: boolean;
  isLoadWorkflowDisabled: boolean;
  onAction: (action: WorkflowAction) => void;
  onLoadWorkflow: () => void;
  onOpenExport: () => void;
  onOpenTab: (tab: EngineTabKey) => void;
  onWorkflowInputChange: (value: string) => void;
  primaryAction: EngineWorkflowControl;
  primaryActionDisabled: boolean;
  projectId: string;
  secondaryControls: EngineWorkflowControl[];
  startWorkflowDisabledReason: string | null;
  workflow: WorkflowExecution | undefined;
  workflowInput: string;
  workflowSummary: WorkflowSummaryCardData | null;
};

export function EnginePageShell({
  banners,
  detailPanel,
  hasWorkflow,
  isActionPending,
  isLoadWorkflowDisabled,
  onAction,
  onLoadWorkflow,
  onOpenExport,
  onOpenTab,
  onWorkflowInputChange,
  primaryAction,
  primaryActionDisabled,
  projectId,
  secondaryControls,
  startWorkflowDisabledReason,
  workflow,
  workflowInput,
  workflowSummary,
}: Readonly<EnginePageShellProps>) {
  return (
    <div className="h-full" style={{ background: "var(--bg-canvas)" }}>
      <PageEntrance>
        <div className="h-full flex flex-col">
          {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent-primary)" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "var(--accent-primary)" }}>
                工作流引擎
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              创作进度
            </h1>
            <div className="flex items-center gap-3 mt-2">
              {workflowSummary ? (
                <>
                  <span className="text-[11px] px-2 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}>
                    {workflowSummary.statusLabel}
                  </span>
                  <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                    {workflowSummary.workflowIdentity}
                  </span>
                </>
              ) : (
                <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                  尚未载入执行批次
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/workspace/project/${projectId}/studio?panel=chapter`}
              className="px-3 py-1.5 text-[11px] font-medium rounded transition-colors"
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-soft)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--bg-muted)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--bg-surface)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              返回创作
            </Link>
            <Link
              href={`/workspace/project/${projectId}/lab`}
              className="px-3 py-1.5 text-[11px] font-medium rounded transition-colors"
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-soft)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--bg-muted)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--bg-surface)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              分析
            </Link>
          </div>
        </div>
      </header>

      {/* Banners */}
      {banners.length > 0 ? (
        <div className="px-6 pt-4 flex flex-col gap-2">
          {banners.map((banner) => (
            <div
              key={banner.id}
              className="px-4 py-2.5 rounded text-[12px] font-medium"
              style={{
                background: banner.tone === "danger" ? "var(--accent-danger-soft)" : "var(--accent-warning-soft)",
                color: banner.tone === "danger" ? "var(--accent-danger)" : "var(--accent-warning)",
                border: `1px solid ${banner.tone === "danger" ? "var(--accent-danger-muted)" : "var(--accent-warning-muted)"}`,
              }}
            >
              {banner.message}
            </div>
          ))}
        </div>
      ) : null}

      {/* Main Content */}
      <div className="flex-1 px-6 py-4 overflow-auto">
        <div className="grid gap-4" style={{ gridTemplateColumns: "minmax(300px, 360px) minmax(0, 1fr)" }}>
          {/* Left: Control Panel */}
          <aside className="space-y-3">
            {/* Primary Action Card */}
            <div className="rounded p-4" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
              <div className="space-y-3">
                <label className="block space-y-1.5">
                  <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>
                    执行批次 ID
                  </span>
                  <input
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded text-[12px] outline-none transition-colors"
                    style={{
                      background: "var(--bg-canvas)",
                      color: "var(--text-primary)",
                      border: "1px solid var(--line-soft)",
                    }}
                    name="workflowId"
                    placeholder="粘贴执行批次 ID"
                    value={workflowInput}
                    onChange={(event) => onWorkflowInputChange(event.target.value)}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = "var(--accent-primary)";
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = "var(--bg-muted)";
                    }}
                  />
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    className="px-3 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: primaryActionDisabled ? "var(--bg-muted)" : "var(--accent-primary)",
                      color: primaryActionDisabled ? "var(--text-tertiary)" : "var(--bg-canvas)",
                    }}
                    disabled={primaryActionDisabled}
                    onClick={() => onAction(primaryAction.action)}
                    title={startWorkflowDisabledReason ?? undefined}
                    type="button"
                  >
                    {isActionPending ? "处理中..." : primaryAction.label}
                  </button>
                  <button
                    className="px-3 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ background: "var(--bg-muted)", color: "var(--text-secondary)" }}
                    disabled={isLoadWorkflowDisabled}
                    onClick={onLoadWorkflow}
                    type="button"
                  >
                    载入批次
                  </button>
                </div>
                {secondaryControls.map((control) => (
                  <button
                    key={control.action}
                    className="w-full px-3 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: control.tone === "danger" ? "var(--accent-danger-soft)" : "var(--bg-muted)",
                      color: control.tone === "danger" ? "var(--accent-danger)" : "var(--text-secondary)",
                      border: control.tone === "danger" ? "1px solid var(--accent-danger-muted)" : "1px solid transparent",
                    }}
                    disabled={isActionPending || control.disabled}
                    onClick={() => onAction(control.action)}
                    type="button"
                  >
                    {control.label}
                  </button>
                ))}
                <button
                  className="w-full px-3 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: "var(--bg-muted)", color: "var(--text-secondary)" }}
                  disabled={!hasWorkflow}
                  onClick={onOpenExport}
                  type="button"
                >
                  导出成稿
                </button>
                {startWorkflowDisabledReason ? (
                  <p className="text-[11px]" style={{ color: "var(--accent-warning)" }}>
                    {startWorkflowDisabledReason}
                  </p>
                ) : null}
              </div>
            </div>

            {/* Status & Summary */}
            {workflow ? (
              <>
                <EngineWorkflowStatusCallout workflow={workflow} onOpenTab={onOpenTab} />
                {workflowSummary ? <EngineWorkflowSummaryCard summary={workflowSummary} /> : null}
                <EngineWorkflowDebugPanel workflow={workflow} />
              </>
            ) : (
              <>
                <PreparationStatusPanel projectId={projectId} />
                <div className="rounded p-6 text-center" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
                  <div className="w-10 h-10 rounded-full mx-auto mb-3 flex items-center justify-center" style={{ background: "var(--bg-surface)" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                    </svg>
                  </div>
                  <p className="text-[13px] font-medium mb-1" style={{ color: "var(--text-tertiary)" }}>
                    还没有推进批次
                  </p>
                  <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                    确认准备状态后启动第一轮推进
                  </p>
                </div>
              </>
            )}
          </aside>

          {/* Right: Detail Panel */}
          <section className="rounded" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--line-soft)" }}>
              <span className="text-[12px] font-medium" style={{ color: "var(--text-secondary)" }}>
                执行详情
              </span>
            </div>
            <div className="p-4">
              {detailPanel}
            </div>
          </section>
        </div>
      </div>
        </div>
    </PageEntrance>
    </div>
  );
}
