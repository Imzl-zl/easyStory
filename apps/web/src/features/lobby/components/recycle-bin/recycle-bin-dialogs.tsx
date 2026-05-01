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
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-lg overflow-hidden"
        style={{ background: "#111418", border: "1px solid #1f2328" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #1f2328" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "#e8e6e3" }}>
            移入回收站
          </h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "#16191e", border: "1px solid #1f2328" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>
              {project.name}
            </p>
          </div>
          <p className="text-[11px]" style={{ color: "#f59e0b" }}>
            项目会移入回收站并保留 30 天，期间可随时恢复。
          </p>
          {errorMessage ? (
            <p className="rounded-md px-3 py-2 text-[11px]" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
              {errorMessage}
            </p>
          ) : null}
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid #1f2328" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b" }}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "移动中..." : "确认移入"}
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "#1f2328", color: "#9ca3af", border: "1px solid #2d3139" }}
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
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-lg overflow-hidden"
        style={{ background: "#111418", border: "1px solid #1f2328" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #1f2328" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "#e8e6e3" }}>
            彻底删除
          </h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "#16191e", border: "1px solid #1f2328" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>
              {project.name}
            </p>
          </div>
          <p className="text-[11px]" style={{ color: "#ef4444" }}>
            删除后无法恢复，所有关联数据将一并清理。
          </p>
          {errorMessage ? (
            <p className="rounded-md px-3 py-2 text-[11px]" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
              {errorMessage}
            </p>
          ) : null}
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid #1f2328" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "删除中..." : "确认删除"}
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "#1f2328", color: "#9ca3af", border: "1px solid #2d3139" }}
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
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-lg overflow-hidden"
        style={{ background: "#111418", border: "1px solid #1f2328" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #1f2328" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "#e8e6e3" }}>
            清空回收站
          </h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "#16191e", border: "1px solid #1f2328" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "#e8e6e3" }}>
              {projectCount} 个项目
            </p>
          </div>
          <p className="text-[11px]" style={{ color: "#ef4444" }}>
            此操作会一次性清空回收站中的全部项目，无法恢复。
          </p>
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid #1f2328" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "清空中..." : "确认清空"}
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "#1f2328", color: "#9ca3af", border: "1px solid #2d3139" }}
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
