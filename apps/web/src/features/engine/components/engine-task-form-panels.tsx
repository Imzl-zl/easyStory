"use client";

import type { RefObject } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildTaskEditorState,
  getTaskEditDisabledReason,
  resolveTaskStatusPresentation,
  type ChapterTaskDraftRow,
  type ChapterTaskEditorState,
} from "@/features/engine/components/engine-task-support";
import type { ChapterTaskView } from "@/lib/api/types";

type TaskFieldProps = Readonly<{
  label: string;
  children: React.ReactNode;
}>;

type EngineTaskEditorSectionProps = {
  editor: ChapterTaskEditorState | null;
  isPending: boolean;
  selectedTask: ChapterTaskView | null;
  setEditor: React.Dispatch<React.SetStateAction<ChapterTaskEditorState | null>>;
  onSave: () => void;
};

type EngineTaskRegenerateSectionProps = {
  draftRows: ChapterTaskDraftRow[];
  disabledReason: string | null;
  isPending: boolean;
  onAddRow: () => void;
  onCreateBlank: () => void;
  onLoadCurrentPlan: () => void;
  onRequestRegenerate: () => void;
  onRemoveRow: (index: number) => void;
  onUpdateRow: (index: number, row: ChapterTaskDraftRow) => void;
  regenerateButtonRef: RefObject<HTMLButtonElement | null>;
};

export function EngineTaskEditorSection({
  editor,
  isPending,
  selectedTask,
  setEditor,
  onSave,
}: Readonly<EngineTaskEditorSectionProps>) {
  const editDisabledReason = selectedTask ? getTaskEditDisabledReason(selectedTask.status) : null;
  const emptyDescription =
    editDisabledReason ?? "从左侧列表选择一个可编辑任务，即可调整标题、摘要、关键角色和关键事件。";

  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">任务编辑器</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          当前只允许编辑可修改状态的任务草稿，不对已确认任务做隐式覆盖。
        </p>
      </div>
      {selectedTask && editor ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status="outline" label={`第 ${selectedTask.chapter_number} 章`} />
            <StatusBadge
              status={resolveTaskStatusPresentation(selectedTask).badgeStatus}
              label={resolveTaskStatusPresentation(selectedTask).badgeLabel}
            />
          </div>
          {editDisabledReason ? (
            <div className="rounded-2xl border border-[rgba(183,121,31,0.2)] bg-[rgba(183,121,31,0.08)] px-4 py-3 text-sm text-[var(--accent-warning)]">
              {editDisabledReason}
            </div>
          ) : null}
          <TaskField label="标题">
            <input
              className="ink-input"
              value={editor.title}
              onChange={(event) => setEditor((current) => (current ? { ...current, title: event.target.value } : current))}
            />
          </TaskField>
          <TaskField label="任务摘要">
            <textarea
              className="ink-textarea min-h-32"
              value={editor.brief}
              onChange={(event) => setEditor((current) => (current ? { ...current, brief: event.target.value } : current))}
            />
          </TaskField>
          <TaskField label="关键角色">
            <input
              className="ink-input"
              value={editor.keyCharacters}
              onChange={(event) =>
                setEditor((current) => (current ? { ...current, keyCharacters: event.target.value } : current))
              }
            />
          </TaskField>
          <TaskField label="关键事件">
            <input
              className="ink-input"
              value={editor.keyEvents}
              onChange={(event) =>
                setEditor((current) => (current ? { ...current, keyEvents: event.target.value } : current))
              }
            />
          </TaskField>
          <div className="flex flex-wrap gap-2">
            <button className="ink-button" disabled={isPending || Boolean(editDisabledReason)} onClick={onSave}>
              {isPending ? "保存中..." : "保存任务"}
            </button>
            <button
              className="ink-button-secondary"
              onClick={() => setEditor(buildTaskEditorState(selectedTask))}
            >
              重置编辑器
            </button>
          </div>
        </div>
      ) : (
        <EmptyState
          title="还没有选中任务"
          description={emptyDescription}
        />
      )}
    </section>
  );
}

export function EngineTaskRegenerateSection({
  draftRows,
  disabledReason,
  isPending,
  onAddRow,
  onCreateBlank,
  onLoadCurrentPlan,
  onRequestRegenerate,
  onRemoveRow,
  onUpdateRow,
  regenerateButtonRef,
}: Readonly<EngineTaskRegenerateSectionProps>) {
  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">重建章节任务</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          这里会覆盖当前活跃 workflow 的章节计划。提交前请确认章节号、标题与摘要已经完整。
        </p>
      </div>
      {disabledReason ? (
        <div className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          {disabledReason}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button className="ink-button-secondary" onClick={onLoadCurrentPlan}>
              载入当前计划
            </button>
            <button className="ink-button-secondary" onClick={onCreateBlank}>
              新建空白计划
            </button>
            <button className="ink-button-secondary" onClick={onAddRow}>
              追加一章
            </button>
            <button
              aria-haspopup="dialog"
              className="ink-button-danger"
              disabled={isPending || draftRows.length === 0}
              onClick={onRequestRegenerate}
              ref={regenerateButtonRef}
              type="button"
            >
              {isPending ? "覆盖中..." : "检查并确认"}
            </button>
          </div>
          {draftRows.length === 0 ? (
            <EmptyState
              title="还没有重建草稿"
              description="载入当前计划或新建章节任务。"
            />
          ) : (
            <div className="space-y-3">
              {draftRows.map((row, index) => (
                <DraftRowEditor
                  key={`${index}-${row.chapterNumber}`}
                  index={index}
                  row={row}
                  onChange={(nextRow) => onUpdateRow(index, nextRow)}
                  onRemove={() => onRemoveRow(index)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function DraftRowEditor({
  index,
  row,
  onChange,
  onRemove,
}: Readonly<{
  index: number;
  row: ChapterTaskDraftRow;
  onChange: (nextRow: ChapterTaskDraftRow) => void;
  onRemove: () => void;
}>) {
  return (
    <article className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.52)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-[var(--text-primary)]">重建草稿 #{index + 1}</p>
        <button className="ink-button-secondary" onClick={onRemove}>
          移除此章
        </button>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <TaskField label="章节号">
          <input
            className="ink-input"
            inputMode="numeric"
            value={row.chapterNumber}
            onChange={(event) => onChange({ ...row, chapterNumber: event.target.value })}
          />
        </TaskField>
        <TaskField label="标题">
          <input
            className="ink-input"
            value={row.title}
            onChange={(event) => onChange({ ...row, title: event.target.value })}
          />
        </TaskField>
      </div>
      <div className="mt-4 space-y-4">
        <TaskField label="任务摘要">
          <textarea
            className="ink-textarea min-h-28"
            value={row.brief}
            onChange={(event) => onChange({ ...row, brief: event.target.value })}
          />
        </TaskField>
        <div className="grid gap-4 md:grid-cols-2">
          <TaskField label="关键角色">
            <input
              className="ink-input"
              value={row.keyCharacters}
              onChange={(event) => onChange({ ...row, keyCharacters: event.target.value })}
            />
          </TaskField>
          <TaskField label="关键事件">
            <input
              className="ink-input"
              value={row.keyEvents}
              onChange={(event) => onChange({ ...row, keyEvents: event.target.value })}
            />
          </TaskField>
        </div>
      </div>
    </article>
  );
}

function TaskField({ label, children }: TaskFieldProps) {
  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      {children}
    </label>
  );
}
