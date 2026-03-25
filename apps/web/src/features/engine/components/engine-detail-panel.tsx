"use client";

import { EngineBillingPanel } from "@/features/engine/components/engine-billing-panel";
import { EngineBlock } from "@/features/engine/components/engine-block";
import { EngineContextPanel } from "@/features/engine/components/engine-context-panel";
import { EngineLogsPanel } from "@/features/engine/components/engine-logs-panel";
import { EngineOverviewPanel } from "@/features/engine/components/engine-overview-panel";
import { EngineReplayPanel } from "@/features/engine/components/engine-replay-panel";
import { EngineReviewPanel } from "@/features/engine/components/engine-review-panel";
import { EngineTaskPanel } from "@/features/engine/components/engine-task-panel";
import {
  listEngineDetailTabs,
  type EngineDetailTabOption,
} from "@/features/engine/components/engine-detail-panel-support";
import type {
  ExecutionLogView,
  NodeExecutionView,
  PromptReplayView,
  TokenUsageView,
  WorkflowBillingSummary,
  WorkflowExecution,
  WorkflowReviewAction,
  WorkflowReviewSummary,
} from "@/lib/api/types";

import type { EngineTabKey } from "./engine-workflow-status-support";

type EngineDetailPanelProps = {
  activeTab: EngineTabKey;
  billing: {
    errorMessage: string | null;
    isLoading: boolean;
    summary: WorkflowBillingSummary | null;
    usages: TokenUsageView[];
  };
  context: {
    projectId: string;
    workflowId: string;
  };
  hasWorkflow: boolean;
  logs: {
    errorMessage: string | null;
    executions: NodeExecutionView[];
    executionLogs: ExecutionLogView[];
    isLoading: boolean;
  };
  onOpenReplayExecution: (executionId: string) => void;
  onOpenTab: (tab: EngineTabKey) => void;
  projectId: string;
  replays: {
    errorMessage: string | null;
    executions: NodeExecutionView[];
    executionsErrorMessage: string | null;
    isExecutionsLoading: boolean;
    isReplaysLoading: boolean;
    onSelectExecutionId: (value: string) => void;
    replays: PromptReplayView[];
    selectedExecution: NodeExecutionView | null;
    selectedExecutionId: string;
  };
  reviews: {
    actions: WorkflowReviewAction[];
    errorMessage: string | null;
    isLoading: boolean;
    summary: WorkflowReviewSummary | null;
  };
  workflow: WorkflowExecution | undefined;
};

export function EngineDetailPanel({
  activeTab,
  billing,
  context,
  hasWorkflow,
  logs,
  onOpenReplayExecution,
  onOpenTab,
  projectId,
  replays,
  reviews,
  workflow,
}: Readonly<EngineDetailPanelProps>) {
  const tabs = listEngineDetailTabs();

  return (
    <div className="space-y-4">
      <nav
        aria-label="引擎详情标签"
        className="flex flex-wrap gap-2"
      >
        {tabs.map((tab) => (
          <DetailTabButton
            key={tab.key}
            isActive={activeTab === tab.key}
            onClick={() => onOpenTab(tab.key)}
            tab={tab}
          />
        ))}
      </nav>
      {activeTab === "overview" ? (
        <EngineBlock title="执行概览">
          <EngineOverviewPanel
            workflow={workflow}
            executions={logs.executions}
            isLoading={logs.isLoading}
            errorMessage={logs.errorMessage}
            onOpenReplayExecution={onOpenReplayExecution}
          />
        </EngineBlock>
      ) : null}
      {activeTab === "tasks" ? (
        <EngineBlock title="章节任务">
          <EngineTaskPanel
            key={context.workflowId || "workflow-empty"}
            projectId={projectId}
            workflow={workflow}
          />
        </EngineBlock>
      ) : null}
      {activeTab === "reviews" ? (
        <EngineBlock title="审核摘要与动作">
          <EngineReviewPanel
            summary={reviews.summary}
            actions={reviews.actions}
            isLoading={reviews.isLoading}
            errorMessage={reviews.errorMessage}
          />
        </EngineBlock>
      ) : null}
      {activeTab === "billing" ? (
        <EngineBlock title="账单摘要与 Token 使用">
          <EngineBillingPanel
            summary={billing.summary}
            usages={billing.usages}
            isLoading={billing.isLoading}
            errorMessage={billing.errorMessage}
          />
        </EngineBlock>
      ) : null}
      {activeTab === "logs" ? (
        <EngineBlock title="节点执行与日志">
          <EngineLogsPanel
            executions={logs.executions}
            logs={logs.executionLogs}
            isLoading={logs.isLoading}
            errorMessage={logs.errorMessage}
            onOpenReplayExecution={onOpenReplayExecution}
          />
        </EngineBlock>
      ) : null}
      {activeTab === "context" ? (
        <EngineBlock title="上下文预览">
          <EngineContextPanel
            projectId={context.projectId}
            workflowId={context.workflowId}
            isWorkflowReady={hasWorkflow}
          />
        </EngineBlock>
      ) : null}
      {activeTab === "replays" ? (
        <EngineBlock title="提示词回放">
          <EngineReplayPanel
            isWorkflowReady={hasWorkflow}
            executions={replays.executions}
            selectedExecutionId={replays.selectedExecutionId}
            onSelectExecutionId={replays.onSelectExecutionId}
            selectedExecution={replays.selectedExecution}
            replays={replays.replays}
            isExecutionsLoading={replays.isExecutionsLoading}
            isReplaysLoading={replays.isReplaysLoading}
            executionsErrorMessage={replays.executionsErrorMessage}
            replaysErrorMessage={replays.errorMessage}
          />
        </EngineBlock>
      ) : null}
    </div>
  );
}

function DetailTabButton({
  isActive,
  onClick,
  tab,
}: Readonly<{
  isActive: boolean;
  onClick: () => void;
  tab: EngineDetailTabOption;
}>) {
  return (
    <button className="ink-tab" data-active={isActive} onClick={onClick}>
      {tab.label}
    </button>
  );
}
