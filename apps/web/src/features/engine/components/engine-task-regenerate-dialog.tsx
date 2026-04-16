"use client";

import type { RefObject } from "react";

import { DialogShell } from "@/components/ui/dialog-shell";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildRegenerateConfirmationItems,
  REGENERATE_CONFIRMATION_MESSAGE,
} from "@/features/engine/components/engine-task-regenerate-support";
import type { ChapterTaskDraft, ChapterTaskView } from "@/lib/api/types";

type EngineTaskRegenerateDialogProps = {
  currentTasks: ChapterTaskView[];
  draftPayload: ChapterTaskDraft[];
  errorMessage: string | null;
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  restoreFocusRef: RefObject<HTMLElement | null>;
};

export function EngineTaskRegenerateDialog({
  currentTasks,
  draftPayload,
  errorMessage,
  isPending,
  onClose,
  onConfirm,
  restoreFocusRef,
}: Readonly<EngineTaskRegenerateDialogProps>) {
  const items = buildRegenerateConfirmationItems(currentTasks, draftPayload);

  return (
    <DialogShell
      title="确认重建章节任务"
      description="重建将覆盖当前计划，请确认后继续。"
      onClose={onClose}
      restoreFocusRef={restoreFocusRef}
    >
      <div className="grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-3">
            <StatusBadge status="failed" label="二次确认" />
            <div className="rounded-2xl border border-accent-danger/15 bg-accent-danger/10 px-4 py-4 text-sm leading-6 text-accent-danger">
              {REGENERATE_CONFIRMATION_MESSAGE}
            </div>
          </div>
          {errorMessage ? (
            <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
              {errorMessage}
            </div>
          ) : null}
          <div className="flex flex-wrap gap-3">
            <button
              className="ink-button-danger"
              disabled={isPending}
              onClick={onConfirm}
              type="button"
            >
              {isPending ? "重建中..." : "确认重建"}
            </button>
            <button
              className="ink-button-secondary"
              disabled={isPending}
              onClick={onClose}
              type="button"
            >
              再检查一下
            </button>
          </div>
        </section>
        <section className="panel-muted space-y-4 p-5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">覆盖影响</h3>
            <p className="text-sm leading-6 text-text-secondary">
              这里只列出本次重建对当前任务真值的直接影响，不替你静默兜底。
            </p>
          </div>
          <div className="space-y-3">
            {items.map((item) => (
              <article
                className="rounded-2xl bg-glass shadow-glass px-4 py-3"
                key={item}
              >
                <p className="text-sm leading-6 text-text-secondary">{item}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </DialogShell>
  );
}
