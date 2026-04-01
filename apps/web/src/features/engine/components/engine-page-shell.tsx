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
    <div className="min-h-screen p-8 [background:radial-gradient(circle_at_top_left,rgba(196,167,125,0.18),transparent_30%),radial-gradient(circle_at_right_20%,rgba(90,154,170,0.16),transparent_28%),linear-gradient(180deg,#f7f1e7_0%,#f4efe7_48%,#f8f6f1_100%)]">
      <section className="hero-card p-9 flex flex-col justify-between gap-6">
        <div className="absolute -right-10 -bottom-14 w-[180px] h-[180px] rounded-full bg-[rgba(90,122,107,0.08)]" />
        <div className="max-w-[620px]">
          <p className="label-overline">推进中心</p>
          <h1 className="mt-4.5 font-serif text-[clamp(2.6rem,5vw,4.4rem)] font-semibold leading-tight">让创作推进本身可见，但别让它盖过作品。</h1>
          <p className="max-w-[580px] mt-4.5 text-[var(--text-secondary)] text-base leading-relaxed">
            在这里查看当前执行批次、推进阻塞、审核和回放。入口语言保持创作语境，不再像控制台。
          </p>
          {workflowSummary ? (
            <div className="flex flex-wrap gap-2 mt-4">
              <StatusBadge status={workflowSummary.statusTone} label={workflowSummary.statusLabel} />
              <StatusBadge status={workflowSummary.modeTone} label={workflowSummary.modeLabel} />
              <StatusBadge status={workflowSummary.runtimeSnapshotTone} label={workflowSummary.runtimeSnapshotLabel} />
            </div>
          ) : null}
          <article className="mt-6 p-5 rounded-[22px] bg-gradient-to-b from-[rgba(250,246,237,0.94)] to-[rgba(247,241,231,0.88)]">
            <p className="label-overline">当前批次</p>
            <h2 className="mt-2 font-serif text-xl font-semibold">{workflowSummary?.workflowIdentity ?? "尚未载入执行批次"}</h2>
            <p className="mt-1.5 text-[var(--text-secondary)] text-sm leading-relaxed">
              {workflowSummary?.description ?? "先确认项目准备状态，再启动一轮新的推进。"}
            </p>
          </article>
        </div>
        <aside className="grid gap-4">
          <label className="grid gap-2">
            <span className="text-[var(--text-secondary)] text-sm font-medium">继续某次执行</span>
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
                className={control.tone === "danger" ? "min-h-[42px] border border-[rgba(178,65,46,0.28)] rounded-4 bg-[rgba(178,65,46,0.06)] text-[var(--accent-danger)] text-sm font-medium cursor-pointer transition-colors hover:bg-[rgba(178,65,46,0.12)]" : "ink-button-secondary"}
                disabled={isActionPending || control.disabled}
                key={control.action}
                onClick={() => onAction(control.action)}
                type="button"
              >
                {control.label}
              </button>
            ))}
          </div>
          {startWorkflowDisabledReason ? <p className="text-[var(--text-muted)] text-xs leading-relaxed">{startWorkflowDisabledReason}</p> : null}
        </aside>
      </section>

      {banners.length > 0 ? (
        <div className="flex flex-col gap-2 mt-4">
          {banners.map((banner) => (
            <div className={`px-4 py-3 rounded-2xl text-sm ${banner.tone === "danger" ? "bg-[rgba(178,65,46,0.1)] text-[var(--accent-danger)]" : "bg-[rgba(196,167,108,0.1)] text-[var(--accent-warning)]"}`} key={banner.id}>
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
                description="准备状态确认后，从这里启动第一轮推进。"
              />
            </>
          )}
        </aside>
        <section className="hero-card">
          <div className="p-6">
            <p className="label-overline">执行详情</p>
            <h2 className="mt-3 font-serif text-2xl font-semibold">按视角查看这一轮推进。</h2>
            <p className="mt-2 text-[var(--text-secondary)] text-sm leading-relaxed">
              概览、章节任务、审核、日志和提示词回放都保留，但它们现在属于作品推进过程的一部分。
            </p>
          </div>
          {detailPanel}
        </section>
      </div>
    </div>
  );
}
