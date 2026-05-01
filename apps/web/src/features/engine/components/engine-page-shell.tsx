"use client";

import Link from "next/link";
import type { ReactNode } from "react";

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
    <div className="h-full flex flex-col" style={{ background: "#111418" }}>
      {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid #1f2328" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#e8b86d" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "#e8b86d" }}>
                工作流引擎
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "#e8e6e3" }}>
              创作进度
            </h1>
            <div className="flex items-center gap-3 mt-2">
              {workflowSummary ? (
                <>
                  <span className="text-[11px] px-2 py-0.5 rounded" style={{ background: "#1f2328", color: "#9ca3af" }}>
                    {workflowSummary.statusLabel}
                  </span>
                  <span className="text-[11px]" style={{ color: "#6b7280" }}>
                    {workflowSummary.workflowIdentity}
                  </span>
                </>
              ) : (
                <span className="text-[11px]" style={{ color: "#6b7280" }}>
                  尚未载入执行批次
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/workspace/project/${projectId}/studio?panel=chapter`}
              className="px-3 py-1.5 text-[11px] font-medium rounded transition-colors"
              style={{ background: "#1f2328", color: "#9ca3af", border: "1px solid #2a2f35" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#2a2f35";
                e.currentTarget.style.color = "#e8e6e3";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "#1f2328";
                e.currentTarget.style.color = "#9ca3af";
              }}
            >
              返回创作
            </Link>
            <Link
              href={`/workspace/project/${projectId}/lab`}
              className="px-3 py-1.5 text-[11px] font-medium rounded transition-colors"
              style={{ background: "#1f2328", color: "#9ca3af", border: "1px solid #2a2f35" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#2a2f35";
                e.currentTarget.style.color = "#e8e6e3";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "#1f2328";
                e.currentTarget.style.color = "#9ca3af";
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
                background: banner.tone === "danger" ? "rgba(220, 38, 38, 0.12)" : "rgba(234, 179, 8, 0.12)",
                color: banner.tone === "danger" ? "#f87171" : "#fbbf24",
                border: `1px solid ${banner.tone === "danger" ? "rgba(220, 38, 38, 0.2)" : "rgba(234, 179, 8, 0.2)"}`,
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
            <div className="rounded p-4" style={{ background: "#1a1d23", border: "1px solid #2a2f35" }}>
              <div className="space-y-3">
                <label className="block space-y-1.5">
                  <span className="text-[11px] font-medium" style={{ color: "#6b7280" }}>
                    执行批次 ID
                  </span>
                  <input
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded text-[12px] outline-none transition-colors"
                    style={{
                      background: "#111418",
                      color: "#e8e6e3",
                      border: "1px solid #2a2f35",
                    }}
                    name="workflowId"
                    placeholder="粘贴执行批次 ID"
                    value={workflowInput}
                    onChange={(event) => onWorkflowInputChange(event.target.value)}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = "#e8b86d";
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = "#2a2f35";
                    }}
                  />
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    className="px-3 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: primaryActionDisabled ? "#2a2f35" : "#e8b86d",
                      color: primaryActionDisabled ? "#6b7280" : "#111418",
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
                    style={{ background: "#2a2f35", color: "#9ca3af" }}
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
                      background: control.tone === "danger" ? "rgba(220, 38, 38, 0.1)" : "#2a2f35",
                      color: control.tone === "danger" ? "#f87171" : "#9ca3af",
                      border: control.tone === "danger" ? "1px solid rgba(220, 38, 38, 0.2)" : "1px solid transparent",
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
                  style={{ background: "#2a2f35", color: "#9ca3af" }}
                  disabled={!hasWorkflow}
                  onClick={onOpenExport}
                  type="button"
                >
                  导出成稿
                </button>
                {startWorkflowDisabledReason ? (
                  <p className="text-[11px]" style={{ color: "#fbbf24" }}>
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
                <div className="rounded p-6 text-center" style={{ background: "#1a1d23", border: "1px solid #2a2f35" }}>
                  <div className="w-10 h-10 rounded-full mx-auto mb-3 flex items-center justify-center" style={{ background: "#1f2328" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4b5563" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                    </svg>
                  </div>
                  <p className="text-[13px] font-medium mb-1" style={{ color: "#6b7280" }}>
                    还没有推进批次
                  </p>
                  <p className="text-[11px]" style={{ color: "#4b5563" }}>
                    确认准备状态后启动第一轮推进
                  </p>
                </div>
              </>
            )}
          </aside>

          {/* Right: Detail Panel */}
          <section className="rounded" style={{ background: "#1a1d23", border: "1px solid #2a2f35" }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid #2a2f35" }}>
              <span className="text-[12px] font-medium" style={{ color: "#9ca3af" }}>
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
  );
}
