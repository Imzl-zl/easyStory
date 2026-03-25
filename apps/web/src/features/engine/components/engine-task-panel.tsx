"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
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
  const [feedback, setFeedback] = useState<string | null>(null);
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
      setFeedback(`第 ${result.chapter_number} 章任务已更新。`);
      setSelectedTaskNumber(result.chapter_number);
      setEditor(buildTaskEditorState(result));
      queryClient.invalidateQueries({ queryKey: ["workflow-tasks", workflowId] });
      queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const regenerateMutation = useMutation({
    mutationFn: (payload: ChapterTaskDraft[]) => regenerateChapterTasks(projectId, payload),
    onSuccess: (result) => {
      const firstTask = result.tasks[0];
      setFeedback(`章节任务计划已重建，当前共 ${result.tasks.length} 章。`);
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
    onError: (error) => setFeedback(getErrorMessage(error)),
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
      setFeedback(disabledReason);
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
      setFeedback(null);
      regenerateMutation.reset();
      setPendingRegeneratePayload(payload);
      setRegenerateConfirmOpen(true);
    } catch (error) {
      setFeedback(getErrorMessage(error));
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
        description="先启动或载入一个 workflow，再在这里查看、编辑或重建章节任务。"
      />
    );
  }

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[1.02fr_0.98fr]">
        <section className="panel-muted space-y-4 p-5" ref={taskListSectionRef} tabIndex={-1}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">当前章节任务</h3>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
                当前载入 workflow 的任务真值。单条任务可编辑，整套计划可覆盖式重建。
              </p>
            </div>
            <StatusBadge status={workflow.status} label={workflow.status} />
          </div>

          {feedback ? (
            <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
              {feedback}
            </div>
          ) : null}

          {tasksQuery.isLoading ? (
            <p className="text-sm text-[var(--text-secondary)]">正在加载章节任务...</p>
          ) : null}
          {tasksQuery.error ? (
            <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
              {getErrorMessage(tasksQuery.error)}
            </div>
          ) : null}

          {hasStaleTasks(tasks) ? (
            <div className="rounded-2xl border border-[rgba(183,121,31,0.2)] bg-[rgba(183,121,31,0.08)] px-4 py-3 text-sm text-[var(--accent-warning)]">
              当前章节任务存在 `stale` 项。根据设计约束，这不是普通警告，必须先重建章节计划再继续使用。
            </div>
          ) : null}

          {tasks.length === 0 && !tasksQuery.isLoading ? (
            <EmptyState
              title="当前没有章节任务"
              description="这通常意味着 chapter_split 还没有产出计划，或当前 workflow 还没有任务真值。"
            />
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => {
                const status = resolveTaskStatusPresentation(task);
                const editDisabledReason = getTaskEditDisabledReason(task.status);
                return (
                  <article
                    key={task.task_id}
                    className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.56)] p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusBadge status="outline" label={`第 ${task.chapter_number} 章`} />
                          <StatusBadge status={status.badgeStatus} label={status.badgeLabel} />
                        </div>
                        <p className="font-medium text-[var(--text-primary)]">{task.title}</p>
                      </div>
                      <button
                        className="ink-button-secondary"
                        disabled={Boolean(editDisabledReason)}
                        onClick={() => startEditingTask(task.chapter_number)}
                        title={editDisabledReason ?? undefined}
                      >
                        编辑此任务
                      </button>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                      {task.brief}
                    </p>
                    <p className="mt-3 text-xs uppercase tracking-[0.14em] text-[var(--text-secondary)]">
                      {status.description}
                    </p>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <div className="space-y-4">
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
