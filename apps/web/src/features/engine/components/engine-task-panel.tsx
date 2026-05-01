"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { EmptyState } from "@/components/ui/empty-state";
import {
  EngineTaskEditorSection,
  EngineTaskRegenerateSection,
} from "@/features/engine/components/engine-task-form-panels";
import { EngineTaskRegenerateDialog } from "@/features/engine/components/engine-task-regenerate-dialog";
import {
  buildDraftRows,
  buildEmptyDraftRow,
  buildTaskEditorState,
  getTaskEditDisabledReason,
  getRegenerateDisabledReason,
  hasStaleTasks,
  nextChapterNumber,
  resolveTaskStatusPresentation,
  toRegeneratePayload,
  toTaskUpdatePayload,
  type ChapterTaskEditorState,
} from "@/features/engine/components/engine-task-support";
import { getErrorMessage } from "@/lib/api/client";
import { listChapterTasks, regenerateChapterTasks, updateChapterTask } from "@/lib/api/workflow";
import type { ChapterTaskDraft, WorkflowExecution } from "@/lib/api/types";

type EngineTaskPanelProps = {
  projectId: string;
  workflow: WorkflowExecution | undefined;
};

export function EngineTaskPanel({ projectId, workflow }: EngineTaskPanelProps) {
  const queryClient = useQueryClient();
  const taskListSectionRef = useRef<HTMLElement | null>(null);
  const regenerateButtonRef = useRef<HTMLButtonElement | null>(null);
  const dialogRestoreFocusRef = useRef<HTMLElement | null>(null);
  const [selectedTaskNumber, setSelectedTaskNumber] = useState<number | null>(null);
  const [editor, setEditor] = useState<ChapterTaskEditorState | null>(null);
  const [draftRows, setDraftRows] = useState(buildDraftRows([]));
  const [pendingRegeneratePayload, setPendingRegeneratePayload] = useState<ChapterTaskDraft[] | null>(
    null,
  );
  const [isRegenerateConfirmOpen, setRegenerateConfirmOpen] = useState(false);
  const workflowId = workflow?.execution_id ?? "";
  const regenerateDisabledReason = getRegenerateDisabledReason(workflow);

  const tasksQuery = useQuery({
    queryKey: ["workflow-tasks", workflowId],
    queryFn: () => listChapterTasks(workflowId),
    enabled: Boolean(workflowId),
  });

  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editor || selectedTaskNumber === null) {
        throw new Error("请先选择一个章节任务再保存。");
      }
      return updateChapterTask(workflowId, selectedTaskNumber, toTaskUpdatePayload(editor));
    },
    onSuccess: (result) => {
      showAppNotice({
        content: `第 ${result.chapter_number} 章任务已更新。`,
        title: "章节任务",
        tone: "success",
      });
      setSelectedTaskNumber(result.chapter_number);
      setEditor(buildTaskEditorState(result));
      queryClient.invalidateQueries({ queryKey: ["workflow-tasks", workflowId] });
      queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "章节任务",
        tone: "danger",
      }),
  });

  const regenerateMutation = useMutation({
    mutationFn: (payload: ChapterTaskDraft[]) => regenerateChapterTasks(projectId, payload),
    onSuccess: (result) => {
      const firstTask = result.tasks[0];
      showAppNotice({
        content: `章节任务计划已重建，当前共 ${result.tasks.length} 章。`,
        title: "章节任务",
        tone: "success",
      });
      dialogRestoreFocusRef.current = taskListSectionRef.current;
      setRegenerateConfirmOpen(false);
      setPendingRegeneratePayload(null);
      setDraftRows(buildDraftRows(result.tasks));
      setSelectedTaskNumber(firstTask?.chapter_number ?? null);
      setEditor(firstTask ? buildTaskEditorState(firstTask) : null);
      queryClient.invalidateQueries({ queryKey: ["workflow", workflowId] });
      queryClient.invalidateQueries({ queryKey: ["workflow-tasks", workflowId] });
      queryClient.invalidateQueries({ queryKey: ["workflow-observability", workflowId] });
      queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "章节任务",
        tone: "danger",
      }),
  });

  const tasks = tasksQuery.data ?? [];
  const selectedTask = tasks.find((task) => task.chapter_number === selectedTaskNumber) ?? null;

  const startEditingTask = (chapterNumber: number) => {
    const task = tasks.find((item) => item.chapter_number === chapterNumber);
    if (!task) {
      return;
    }
    const disabledReason = getTaskEditDisabledReason(task.status);
    if (disabledReason) {
      showAppNotice({
        content: disabledReason,
        title: "章节任务",
        tone: "warning",
      });
      return;
    }
    setSelectedTaskNumber(task.chapter_number);
    setEditor(buildTaskEditorState(task));
  };

  const resetDraftRows = () => {
    setDraftRows(buildDraftRows(tasks));
  };

  const createBlankDraftRows = () => {
    setDraftRows([buildEmptyDraftRow()]);
  };

  const requestRegenerate = () => {
    try {
      const payload = toRegeneratePayload(draftRows);
      dialogRestoreFocusRef.current = regenerateButtonRef.current;
      regenerateMutation.reset();
      setPendingRegeneratePayload(payload);
      setRegenerateConfirmOpen(true);
    } catch (error) {
      showAppNotice({
        content: getErrorMessage(error),
        title: "章节任务",
        tone: "danger",
      });
    }
  };

  const closeRegenerateConfirm = () => {
    if (regenerateMutation.isPending) {
      return;
    }
    dialogRestoreFocusRef.current = regenerateButtonRef.current;
    regenerateMutation.reset();
    setPendingRegeneratePayload(null);
    setRegenerateConfirmOpen(false);
  };

  if (!workflow) {
    return (
      <EmptyState
        title="尚未载入章节任务"
        description="启动工作流后查看。"
      />
    );
  }

  return (
    <>
      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <section ref={taskListSectionRef} tabIndex={-1}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[12px] font-medium" style={{ color: "var(--text-tertiary)" }}>
              当前章节任务
            </span>
            <StatusPill tone={workflow.status} label={workflow.status} />
          </div>

          {tasksQuery.isLoading ? (
            <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>正在加载章节任务...</p>
          ) : null}
          {tasksQuery.error ? (
            <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {getErrorMessage(tasksQuery.error)}
            </div>
          ) : null}

          {hasStaleTasks(tasks) ? (
            <div className="rounded px-3 py-2 text-[11px] mb-2" style={{ background: "var(--accent-warning-soft)", color: "var(--accent-warning)" }}>
              部分任务已过期，请重建章节计划后继续。
            </div>
          ) : null}

          {tasks.length === 0 && !tasksQuery.isLoading ? (
            <EmptyState
              title="当前没有章节任务"
              description="工作流尚未生成章节计划。"
            />
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => {
                const status = resolveTaskStatusPresentation(task);
                const editDisabledReason = getTaskEditDisabledReason(task.status);
                return (
                  <article
                    key={task.task_id}
                    className="rounded p-3 cursor-pointer transition-colors"
                    style={{
                      background: selectedTaskNumber === task.chapter_number ? "var(--line-soft)" : "var(--bg-canvas)",
                      border: `1px solid ${selectedTaskNumber === task.chapter_number ? "var(--bg-muted)" : "var(--line-soft)"}`,
                    }}
                    onClick={() => startEditingTask(task.chapter_number)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}>
                            第 {task.chapter_number} 章
                          </span>
                          <StatusPill tone={status.badgeStatus} label={status.badgeLabel} />
                        </div>
                        <p className="text-[12px] font-medium truncate" style={{ color: "var(--text-primary)" }}>{task.title}</p>
                      </div>
                      <button
                        className="flex-shrink-0 px-2 py-1 rounded text-[10px] font-medium transition-colors disabled:opacity-40"
                        style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
                        disabled={Boolean(editDisabledReason)}
                        onClick={(e) => {
                          e.stopPropagation();
                          startEditingTask(task.chapter_number);
                        }}
                        title={editDisabledReason ?? undefined}
                      >
                        编辑
                      </button>
                    </div>
                    <p className="mt-1.5 text-[11px] leading-relaxed line-clamp-2" style={{ color: "var(--text-tertiary)" }}>
                      {task.brief}
                    </p>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <div className="space-y-3">
          <EngineTaskEditorSection
            editor={editor}
            isPending={updateMutation.isPending}
            selectedTask={selectedTask}
            setEditor={setEditor}
            onSave={() => updateMutation.mutate()}
          />
          <EngineTaskRegenerateSection
            disabledReason={regenerateDisabledReason}
            draftRows={draftRows}
            isPending={regenerateMutation.isPending}
            onAddRow={() =>
              setDraftRows((current) => [
                ...current,
                buildEmptyDraftRow(nextChapterNumber(current)),
              ])
            }
            onCreateBlank={createBlankDraftRows}
            onLoadCurrentPlan={resetDraftRows}
            onRequestRegenerate={requestRegenerate}
            onRemoveRow={(index) =>
              setDraftRows((current) =>
                current.filter((_, itemIndex) => itemIndex !== index),
              )
            }
            onUpdateRow={(index, row) =>
              setDraftRows((current) =>
                current.map((item, itemIndex) => (itemIndex === index ? row : item)),
              )
            }
            regenerateButtonRef={regenerateButtonRef}
          />
        </div>
      </div>
      {isRegenerateConfirmOpen && pendingRegeneratePayload ? (
        <EngineTaskRegenerateDialog
          currentTasks={tasks}
          draftPayload={pendingRegeneratePayload}
          errorMessage={regenerateMutation.error ? getErrorMessage(regenerateMutation.error) : null}
          isPending={regenerateMutation.isPending}
          onClose={closeRegenerateConfirm}
          onConfirm={() => regenerateMutation.mutate(pendingRegeneratePayload)}
          restoreFocusRef={dialogRestoreFocusRef}
        />
      ) : null}
    </>
  );
}

function StatusPill({ tone, label }: { tone: string; label: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "var(--accent-success-soft)", text: "var(--accent-success)" },
    failed: { bg: "var(--accent-danger-soft)", text: "var(--accent-danger)" },
    warning: { bg: "var(--accent-warning-soft)", text: "var(--accent-warning)" },
    active: { bg: "var(--accent-primary-soft)", text: "var(--accent-primary)" },
    outline: { bg: "var(--line-soft)", text: "var(--text-secondary)" },
    draft: { bg: "var(--line-soft)", text: "var(--text-tertiary)" },
  };
  const c = colors[tone] || colors.outline;
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-medium"
      style={{ background: c.bg, color: c.text }}
    >
      {label}
    </span>
  );
}
