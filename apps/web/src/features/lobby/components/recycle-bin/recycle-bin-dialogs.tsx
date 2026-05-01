"use client";

import type { ProjectSummary } from "@/lib/api/types";

/* ============================================================
   Soft Delete Confirm Dialog
   ============================================================ */

type ProjectDeleteConfirmDialogProps = {
  errorMessage: string | null;
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  project: ProjectSummary;
};

export function ProjectDeleteConfirmDialog({
  errorMessage,
  isPending,
  onClose,
  onConfirm,
  project,
}: Readonly<ProjectDeleteConfirmDialogProps>) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "var(--overlay-bg)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-lg overflow-hidden"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--line-soft)" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
            移入回收站
          </h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
              {project.name}
            </p>
          </div>
          <p className="text-[11px]" style={{ color: "var(--accent-warning)" }}>
            项目会移入回收站并保留 30 天，期间可随时恢复。
          </p>
          {errorMessage ? (
            <p className="rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {errorMessage}
            </p>
          ) : null}
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid var(--line-soft)" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--accent-warning-soft)", color: "var(--accent-warning)" }}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "移动中..." : "确认移入"}
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
            onClick={onClose}
            type="button"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Physical Delete Confirm Dialog
   ============================================================ */

type RecycleBinDeleteDialogProps = {
  errorMessage: string | null;
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "var(--overlay-bg)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-lg overflow-hidden"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--line-soft)" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
            彻底删除
          </h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
              {project.name}
            </p>
          </div>
          <p className="text-[11px]" style={{ color: "var(--accent-danger)" }}>
            删除后无法恢复，所有关联数据将一并清理。
          </p>
          {errorMessage ? (
            <p className="rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {errorMessage}
            </p>
          ) : null}
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid var(--line-soft)" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "删除中..." : "确认删除"}
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
            onClick={onClose}
            type="button"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Clear Recycle Bin Dialog
   ============================================================ */

type RecycleBinClearDialogProps = {
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
  projectCount: number;
};

export function RecycleBinClearDialog({
  isPending,
  onClose,
  onConfirm,
  projectCount,
}: Readonly<RecycleBinClearDialogProps>) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "var(--overlay-bg)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-lg overflow-hidden"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--line-soft)" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
            清空回收站
          </h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
              {projectCount} 个项目
            </p>
          </div>
          <p className="text-[11px]" style={{ color: "var(--accent-danger)" }}>
            此操作会一次性清空回收站中的全部项目，无法恢复。
          </p>
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid var(--line-soft)" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "清空中..." : "确认清空"}
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
            onClick={onClose}
            type="button"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
