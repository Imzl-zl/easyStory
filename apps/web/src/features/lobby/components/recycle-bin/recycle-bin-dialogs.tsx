"use client";

import { DialogShell } from "@/components/ui/dialog-shell";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  formatProjectTrashDeadline,
  formatProjectTrashTime,
} from "@/features/lobby/components/projects/lobby-project-support";
import type { ProjectSummary } from "@/lib/api/types";

type RecycleBinDeleteDialogProps = {
  errorMessage?: string | null;
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  project: ProjectSummary;
};

type RecycleBinClearDialogProps = {
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  projectCount: number;
};

type ProjectDeleteConfirmDialogProps = {
  errorMessage?: string | null;
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  project: ProjectSummary;
};

export function RecycleBinDeleteDialog({
  errorMessage,
  isPending,
  onClose,
  onConfirm,
  project,
}: Readonly<RecycleBinDeleteDialogProps>) {
  return (
    <DialogShell
      title="确认彻底删除项目"
      description="删除后无法恢复，项目关联数据会一并清理。"
      closeDisabled={isPending}
      onClose={onClose}
    >
      <div className="space-y-4">
        <div className="space-y-3 rounded-2xl border border-accent-danger/15 bg-accent-danger/10 p-4">
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="failed" label="不可恢复" />
            <StatusBadge status="archived" label="回收站" />
          </div>
          <p className="text-base font-medium text-text-primary">{project.name}</p>
          <p className="text-sm leading-6 text-text-secondary">
            删除时间：{formatProjectTrashTime(project.deleted_at)} · 保留截止：
            {formatProjectTrashDeadline(project.deleted_at)}
          </p>
          <p className="text-sm leading-6 text-text-secondary">
            会同时清理正文、工作流、导出、事实、账单、审计和项目级凭证。
          </p>
        </div>
        {errorMessage ? (
          <div className="callout-danger text-sm leading-6 text-accent-danger">{errorMessage}</div>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <button className="ink-button-danger" disabled={isPending} onClick={onConfirm} type="button">
            {isPending ? "删除中..." : "确认彻底删除"}
          </button>
          <button className="ink-button-secondary" disabled={isPending} onClick={onClose} type="button">
            先保留
          </button>
        </div>
      </div>
    </DialogShell>
  );
}

export function ProjectDeleteConfirmDialog({
  errorMessage,
  isPending,
  onClose,
  onConfirm,
  project,
}: Readonly<ProjectDeleteConfirmDialogProps>) {
  return (
    <DialogShell
      title="确认删除项目"
      description="删除后项目会移入回收站，可以在回收站中恢复。"
      closeDisabled={isPending}
      onClose={onClose}
    >
      <div className="space-y-4">
        <div className="space-y-3 rounded-2xl border border-accent-warning/20 bg-accent-warning/8 p-4">
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="archived" label="移入回收站" />
          </div>
          <p className="text-base font-medium text-text-primary">{project.name}</p>
          <p className="text-sm leading-6 text-text-secondary">
            删除后项目会保留在回收站中，关联数据不会清理，随时可以恢复。
          </p>
        </div>
        {errorMessage ? (
          <div className="callout-danger text-sm leading-6 text-accent-danger">{errorMessage}</div>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <button className="ink-button-danger" disabled={isPending} onClick={onConfirm} type="button">
            {isPending ? "删除中..." : "确认删除"}
          </button>
          <button className="ink-button-secondary" disabled={isPending} onClick={onClose} type="button">
            先保留
          </button>
        </div>
      </div>
    </DialogShell>
  );
}

export function RecycleBinClearDialog({
  isPending,
  onClose,
  onConfirm,
  projectCount,
}: Readonly<RecycleBinClearDialogProps>) {
  return (
    <DialogShell
      title="确认清空回收站"
      description="会彻底删除当前账号回收站中的所有项目。"
      closeDisabled={isPending}
      onClose={onClose}
    >
      <div className="space-y-4">
        <div className="space-y-3 rounded-2xl border border-accent-danger/15 bg-accent-danger/10 p-4">
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="failed" label="批量清理" />
            <StatusBadge status="archived" label={`${projectCount} 个项目`} />
          </div>
          <p className="text-sm leading-6 text-text-secondary">
            此操作会一次性清空回收站中的全部项目及其关联数据，无法恢复。
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="ink-button-danger" disabled={isPending} onClick={onConfirm} type="button">
            {isPending ? "清空中..." : "确认清空"}
          </button>
          <button className="ink-button-secondary" disabled={isPending} onClick={onClose} type="button">
            先保留
          </button>
        </div>
      </div>
    </DialogShell>
  );
}
