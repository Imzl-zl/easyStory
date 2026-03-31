"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";

import styles from "./engine-page-shell.module.css";
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
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroBody}>
          <p className={styles.eyebrow}>推进中心</p>
          <h1 className={styles.heroTitle}>让创作推进本身可见，但别让它盖过作品。</h1>
          <p className={styles.heroDescription}>
            在这里查看当前执行批次、推进阻塞、审核和回放。入口语言保持创作语境，不再像控制台。
          </p>
          {workflowSummary ? (
            <div className={styles.badgeRow}>
              <StatusBadge status={workflowSummary.statusTone} label={workflowSummary.statusLabel} />
              <StatusBadge status={workflowSummary.modeTone} label={workflowSummary.modeLabel} />
              <StatusBadge status={workflowSummary.runtimeSnapshotTone} label={workflowSummary.runtimeSnapshotLabel} />
            </div>
          ) : null}
          <article className={styles.identityCard}>
            <p className={styles.identityLabel}>当前批次</p>
            <h2 className={styles.identityTitle}>{workflowSummary?.workflowIdentity ?? "尚未载入执行批次"}</h2>
            <p className={styles.identityDescription}>
              {workflowSummary?.description ?? "先确认项目准备状态，再启动一轮新的推进。"}
            </p>
          </article>
        </div>
        <aside className={styles.controlPanel}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>继续某次执行</span>
            <input
              autoComplete="off"
              className={`ink-input ${styles.input}`}
              name="workflowId"
              placeholder="粘贴执行批次 ID"
              value={workflowInput}
              onChange={(event) => onWorkflowInputChange(event.target.value)}
            />
          </label>
          <div className={styles.actionGrid}>
            <button className={styles.primaryButton} disabled={primaryActionDisabled} onClick={() => onAction(primaryAction.action)} title={startWorkflowDisabledReason ?? undefined} type="button">
              {isActionPending ? "处理中..." : primaryAction.label}
            </button>
            <button className="ink-button-secondary" disabled={isLoadWorkflowDisabled} onClick={onLoadWorkflow} type="button">
              载入批次
            </button>
            <button className="ink-button-secondary" disabled={!hasWorkflow} onClick={onOpenExport} type="button">
              导出成稿
            </button>
            <Link className="ink-button-secondary" href={`/workspace/project/${projectId}/studio?panel=chapter`}>
              返回创作
            </Link>
            {secondaryControls.map((control) => (
              <button
                className={control.tone === "danger" ? styles.dangerButton : "ink-button-secondary"}
                disabled={isActionPending || control.disabled}
                key={control.action}
                onClick={() => onAction(control.action)}
                type="button"
              >
                {control.label}
              </button>
            ))}
          </div>
          {startWorkflowDisabledReason ? <p className={styles.controlHint}>{startWorkflowDisabledReason}</p> : null}
        </aside>
      </section>

      {banners.length > 0 ? (
        <div className={styles.bannerStack}>
          {banners.map((banner) => (
            <div className={styles.banner} data-tone={banner.tone} key={banner.id}>
              {banner.message}
            </div>
          ))}
        </div>
      ) : null}

      <div className={styles.layout}>
        <aside className={styles.sidebar}>
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
        <section className={styles.detailStage}>
          <div className={styles.detailHeader}>
            <p className={styles.detailEyebrow}>执行详情</p>
            <h2 className={styles.detailTitle}>按视角查看这一轮推进。</h2>
            <p className={styles.detailDescription}>
              概览、章节任务、审核、日志和提示词回放都保留，但它们现在属于作品推进过程的一部分。
            </p>
          </div>
          {detailPanel}
        </section>
      </div>
    </div>
  );
}
