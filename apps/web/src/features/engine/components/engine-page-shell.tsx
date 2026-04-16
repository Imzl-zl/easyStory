"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
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
    <div className="min-h-screen p-8 [background:var(--bg-engine-page-gradient)]">
      <section className="hero-card p-9 flex flex-col justify-between gap-6">
        <div className="absolute -right-10 -bottom-14 w-[180px] h-[180px] rounded-full bg-accent-soft" />
        <div className="max-w-[620px]">
          <p className="label-overline">推进中心</p>
          <h1 className="mt-4.5 font-serif text-[clamp(2.6rem,5vw,4.4rem)] font-semibold leading-tight">创作进度</h1>
          {workflowSummary ? (
            <div className="flex flex-wrap gap-2 mt-4">
              <StatusBadge status={workflowSummary.statusTone} label={workflowSummary.statusLabel} />
              <StatusBadge status={workflowSummary.modeTone} label={workflowSummary.modeLabel} />
              <StatusBadge status={workflowSummary.runtimeSnapshotTone} label={workflowSummary.runtimeSnapshotLabel} />
            </div>
          ) : null}
          <article className="mt-6 p-5 rounded-2xl bg-gradient-to-b from-glass-heavy to-glass">
            <p className="label-overline">当前批次</p>
            <h2 className="mt-2 font-serif text-xl font-semibold">{workflowSummary?.workflowIdentity ?? "尚未载入执行批次"}</h2>
            <p className="mt-1.5 text-text-secondary text-sm leading-relaxed">
              {workflowSummary?.description ?? "先确认项目准备状态，再启动一轮新的推进。"}
            </p>
          </article>
        </div>
        <aside className="grid gap-4">
          <label className="grid gap-2">
            <span className="text-text-secondary text-sm font-medium">继续某次执行</span>
            <input
              autoComplete="off"
              className="ink-input w-full"
              name="workflowId"
              placeholder="粘贴执行批次 ID"
              value={workflowInput}
              onChange={(event) => onWorkflowInputChange(event.target.value)}
            />
          </label>
          <div className="grid grid-cols-2 gap-2.5">
            <button className="ink-button-hero w-full" disabled={primaryActionDisabled} onClick={() => onAction(primaryAction.action)} title={startWorkflowDisabledReason ?? undefined} type="button">
              {isActionPending ? "处理中..." : primaryAction.label}
            </button>
            <button className="ink-button-secondary" disabled={isLoadWorkflowDisabled} onClick={onLoadWorkflow} type="button">
              载入批次
            </button>
            <button className="ink-button-secondary" disabled={!hasWorkflow} onClick={onOpenExport} type="button">
              导出成稿
            </button>
            <Link className="ink-button-secondary text-center" href={`/workspace/project/${projectId}/studio?panel=chapter`}>
              返回创作
            </Link>
            {secondaryControls.map((control) => (
              <button
                className={control.tone === "danger" ? "min-h-[42px] border border-accent-danger/25 rounded-4 bg-accent-danger/5 text-accent-danger text-sm font-medium cursor-pointer transition-colors hover:bg-accent-danger/10" : "ink-button-secondary"}
                disabled={isActionPending || control.disabled}
                key={control.action}
                onClick={() => onAction(control.action)}
                type="button"
              >
                {control.label}
              </button>
            ))}
          </div>
          {startWorkflowDisabledReason ? <p className="text-text-tertiary text-xs leading-relaxed">{startWorkflowDisabledReason}</p> : null}
        </aside>
      </section>

      {banners.length > 0 ? (
        <div className="flex flex-col gap-2 mt-4">
          {banners.map((banner) => (
            <div className={`px-4 py-3 rounded-2xl text-sm ${banner.tone === "danger" ? "bg-accent-danger/10 text-accent-danger" : "bg-accent-warning/10 text-accent-warning"}`} key={banner.id}>
              {banner.message}
            </div>
          ))}
        </div>
      ) : null}

      <div className="grid gap-6 max-w-[1240px] min-h-[calc(100vh-64px)] mx-auto mt-6 [grid-template-columns:minmax(0,1.15fr)_minmax(360px,460px)]">
        <aside className="space-y-4">
          {workflow ? (
            <>
              <EngineWorkflowStatusCallout workflow={workflow} onOpenTab={onOpenTab} />
              {workflowSummary ? <EngineWorkflowSummaryCard summary={workflowSummary} /> : null}
              <EngineWorkflowDebugPanel workflow={workflow} />
            </>
          ) : (
            <>
              <PreparationStatusPanel projectId={projectId} />
              <EmptyState
                title="还没有推进批次"
                description="确认准备状态后启动第一轮推进。"
              />
            </>
          )}
        </aside>
        <section className="hero-card">
          <div className="p-6">
            <p className="label-overline">执行详情</p>
            <h2 className="mt-3 font-serif text-2xl font-semibold">推进详情</h2>
          </div>
          {detailPanel}
        </section>
      </div>
    </div>
  );
}
