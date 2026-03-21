"use client";
import { useMemo, useState, useTransition } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EngineBlock } from "@/features/engine/components/engine-block";
import { getWorkflowBillingSummary, listWorkflowTokenUsages } from "@/lib/api/billing";
import { getErrorMessage } from "@/lib/api/client";
import { previewWorkflowContext } from "@/lib/api/context";
import { createWorkflowExports, listProjectExports } from "@/lib/api/export";
import { listWorkflowExecutions, listWorkflowLogs, listPromptReplays } from "@/lib/api/observability";
import { getWorkflowReviewSummary, listWorkflowReviewActions } from "@/lib/api/review";
import { getWorkflow, listChapterTasks, pauseWorkflow, resumeWorkflow, startWorkflow, cancelWorkflow } from "@/lib/api/workflow";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";
import { EngineExportPanel } from "@/features/engine/components/engine-export-panel";
import { resolveEngineWorkflowControls, shouldPollWorkflow } from "@/features/engine/components/engine-workflow-controls";

const TABS = ["overview", "tasks", "reviews", "billing", "logs", "context", "replays"] as const;

type EnginePageProps = {
  projectId: string;
};
export function EnginePage({ projectId }: EnginePageProps) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const tab = (searchParams.get("tab") ?? "overview") as (typeof TABS)[number];
  const exportOpen = searchParams.get("export") === "1";
  const lastWorkflowByProject = useWorkspaceStore((state) => state.lastWorkflowByProject);
  const setLastWorkflow = useWorkspaceStore((state) => state.setLastWorkflow);
  const workflowId = searchParams.get("workflow") ?? lastWorkflowByProject[projectId] ?? "";
  const [workflowInput, setWorkflowInput] = useState(workflowId);
  const [contextNodeId, setContextNodeId] = useState("");
  const [contextChapter, setContextChapter] = useState("");
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const setParams = (patches: Record<string, string | null>) => {
    startTransition(() => {
      const next = new URLSearchParams(searchParams.toString());
      Object.entries(patches).forEach(([key, value]) => {
        if (value === null) {
          next.delete(key);
          return;
        }
        next.set(key, value);
      });
      router.replace(`${pathname}?${next.toString()}`);
    });
  };

  const workflowQuery = useQuery({
    queryKey: ["workflow", workflowId],
    queryFn: () => getWorkflow(workflowId),
    enabled: Boolean(workflowId),
    refetchInterval: (query) => (shouldPollWorkflow(query.state.data?.status) ? 5000 : false),
  });

  const workflowControls = resolveEngineWorkflowControls(workflowQuery.data);
  const hasWorkflow = Boolean(workflowId && workflowQuery.data);
  const chapterTasksQuery = useQuery({
    queryKey: ["workflow-tasks", workflowId],
    queryFn: () => listChapterTasks(workflowId),
    enabled: hasWorkflow,
  });
  const reviewsQuery = useQuery({
    queryKey: ["workflow-reviews", workflowId],
    queryFn: () => Promise.all([getWorkflowReviewSummary(workflowId), listWorkflowReviewActions(workflowId)]),
    enabled: hasWorkflow && tab === "reviews",
  });
  const billingQuery = useQuery({
    queryKey: ["workflow-billing", workflowId],
    queryFn: () => Promise.all([getWorkflowBillingSummary(workflowId), listWorkflowTokenUsages(workflowId)]),
    enabled: hasWorkflow && tab === "billing",
  });
  const logsQuery = useQuery({
    queryKey: ["workflow-observability", workflowId],
    queryFn: () => Promise.all([listWorkflowExecutions(workflowId), listWorkflowLogs(workflowId)]),
    enabled: hasWorkflow && (tab === "logs" || tab === "replays" || tab === "overview"),
    refetchInterval: shouldPollWorkflow(workflowQuery.data?.status) ? 5000 : false,
  });
  const exportsQuery = useQuery({
    queryKey: ["project-exports", projectId],
    queryFn: () => listProjectExports(projectId),
    enabled: hasWorkflow,
  });
  const promptReplayQuery = useQuery({
    queryKey: ["prompt-replays", workflowId, selectedExecutionId],
    queryFn: () => listPromptReplays(workflowId, selectedExecutionId),
    enabled: hasWorkflow && tab === "replays" && Boolean(selectedExecutionId),
  });

  const actionMutation = useMutation({
    mutationFn: async (action: "start" | "pause" | "resume" | "cancel") => {
      if (action === "start") {
        return startWorkflow(projectId);
      }
      if (action === "pause") {
        return pauseWorkflow(workflowId);
      }
      if (action === "resume") {
        return resumeWorkflow(workflowId);
      }
      return cancelWorkflow(workflowId);
    },
    onSuccess: (result) => {
      setFeedback("工作流状态已更新。");
      setLastWorkflow(projectId, result.execution_id);
      setWorkflowInput(result.execution_id);
      setParams({ workflow: result.execution_id });
      queryClient.invalidateQueries({ queryKey: ["workflow"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-observability"] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const contextMutation = useMutation({
    mutationFn: () =>
      previewWorkflowContext(workflowId, {
        node_id: contextNodeId,
        chapter_number: contextChapter ? Number(contextChapter) : undefined,
      }),
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const exportMutation = useMutation({
    mutationFn: () => createWorkflowExports(workflowId, { formats: ["txt", "markdown"] }),
    onSuccess: () => {
      setFeedback("导出任务已创建。");
      queryClient.invalidateQueries({ queryKey: ["project-exports", projectId] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const selectedExecution = useMemo(
    () => logsQuery.data?.[0].find((item) => item.id === selectedExecutionId) ?? null,
    [logsQuery.data, selectedExecutionId],
  );

  return (
    <div className="space-y-6">
      <SectionCard
        title="Engine"
        description="执行控制台优先回答三个问题：现在在跑什么、为何暂停、是否可以继续。"
        action={
          <div className="flex flex-wrap gap-2">
            {workflowQuery.data ? <StatusBadge status={workflowQuery.data.status} /> : null}
            <button
              className="ink-button"
              disabled={actionMutation.isPending || workflowControls.primary.disabled}
              onClick={() => actionMutation.mutate(workflowControls.primary.action)}
            >
              {actionMutation.isPending ? "处理中..." : workflowControls.primary.label}
            </button>
            {workflowControls.secondary.map((control) => (
              <button
                key={control.action}
                className={control.tone === "danger" ? "ink-button-danger" : "ink-button-secondary"}
                disabled={actionMutation.isPending || control.disabled}
                onClick={() => actionMutation.mutate(control.action)}
              >
                {control.label}
              </button>
            ))}
          </div>
        }
      >
        <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <div className="space-y-4">
            <label className="block space-y-2">
              <span className="label-text">当前 workflow id</span>
              <input className="ink-input" value={workflowInput} onChange={(event) => setWorkflowInput(event.target.value)} />
            </label>
            <div className="flex flex-wrap gap-2">
              <button className="ink-button-secondary" disabled={!workflowInput || isPending} onClick={() => setParams({ workflow: workflowInput })}>
                载入已有 workflow
              </button>
              <button className="ink-button-secondary" onClick={() => setParams({ export: exportOpen ? null : "1" })}>
                {exportOpen ? "关闭导出面板" : "打开导出面板"}
              </button>
              <Link className="ink-button-secondary" href={`/workspace/project/${projectId}/studio?panel=chapter`}>
                返回 Studio
              </Link>
            </div>
            {feedback ? (
              <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
                {feedback}
              </div>
            ) : null}
            {workflowQuery.error ? (
              <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
                {getErrorMessage(workflowQuery.error)}
              </div>
            ) : null}
            {workflowQuery.data ? <CodeBlock value={workflowQuery.data} /> : <EmptyState title="尚未载入工作流" description="先启动工作流，或输入已有 workflow id 后载入。" />}
          </div>

          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {TABS.map((item) => (
                <button key={item} className="ink-tab" data-active={tab === item} onClick={() => setParams({ tab: item })}>
                  {item}
                </button>
              ))}
            </div>
            {tab === "overview" ? (
              <EngineBlock title="执行概览">
                <CodeBlock value={logsQuery.data?.[0] ?? workflowQuery.data?.nodes ?? []} />
              </EngineBlock>
            ) : null}
            {tab === "tasks" ? (
              <EngineBlock title="章节任务">
                {chapterTasksQuery.data?.length ? <CodeBlock value={chapterTasksQuery.data} /> : <EmptyState title="没有章节任务" description="当前工作流尚未生成章节任务。" />}
              </EngineBlock>
            ) : null}
            {tab === "reviews" ? (
              <EngineBlock title="审核摘要与动作">
                <CodeBlock value={{ summary: reviewsQuery.data?.[0] ?? null, actions: reviewsQuery.data?.[1] ?? [] }} />
              </EngineBlock>
            ) : null}
            {tab === "billing" ? (
              <EngineBlock title="账单摘要与 Token 使用">
                <CodeBlock value={{ summary: billingQuery.data?.[0] ?? null, usages: billingQuery.data?.[1] ?? [] }} />
              </EngineBlock>
            ) : null}
            {tab === "logs" ? (
              <EngineBlock title="节点执行与日志">
                <CodeBlock value={{ executions: logsQuery.data?.[0] ?? [], logs: logsQuery.data?.[1] ?? [] }} />
              </EngineBlock>
            ) : null}
            {tab === "context" ? (
              <EngineBlock title="上下文预览">
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="block space-y-2">
                      <span className="label-text">node_id</span>
                      <input className="ink-input" value={contextNodeId} onChange={(event) => setContextNodeId(event.target.value)} />
                    </label>
                    <label className="block space-y-2">
                      <span className="label-text">chapter_number</span>
                      <input className="ink-input" inputMode="numeric" value={contextChapter} onChange={(event) => setContextChapter(event.target.value)} />
                    </label>
                  </div>
                  <button className="ink-button" disabled={contextMutation.isPending || !hasWorkflow} onClick={() => contextMutation.mutate()}>
                    {contextMutation.isPending ? "预览中..." : "预览上下文"}
                  </button>
                  {contextMutation.data ? <CodeBlock value={contextMutation.data} /> : null}
                </div>
              </EngineBlock>
            ) : null}
            {tab === "replays" ? (
              <EngineBlock title="Prompt 回放">
                <div className="space-y-4">
                  <select className="ink-select" value={selectedExecutionId} onChange={(event) => setSelectedExecutionId(event.target.value)}>
                    <option value="">选择 node execution</option>
                    {logsQuery.data?.[0].map((execution) => (
                      <option key={execution.id} value={execution.id}>
                        {execution.node_id} · {execution.status}
                      </option>
                    ))}
                  </select>
                  {selectedExecution ? <CodeBlock value={selectedExecution} /> : null}
                  {promptReplayQuery.data ? <CodeBlock value={promptReplayQuery.data} /> : null}
                </div>
              </EngineBlock>
            ) : null}
          </div>
        </div>
      </SectionCard>

      {exportOpen ? (
        <EngineExportPanel
          disabled={!hasWorkflow}
          exports={exportsQuery.data}
          isPending={exportMutation.isPending}
          onCreate={() => exportMutation.mutate()}
        />
      ) : null}
    </div>
  );
}
