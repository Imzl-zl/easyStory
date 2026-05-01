"use client";

import { useState } from "react";
import Link from "next/link";

import { PageEntrance } from "@/components/ui/page-entrance";
import { useLobbyProjectModel } from "@/features/lobby/components/projects/lobby-project-model";
import { RecycleBinClearDialog } from "@/features/lobby/components/recycle-bin/recycle-bin-dialogs";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectSummary } from "@/lib/api/types";

export function RecycleBinPage() {
  const [isClearDialogOpen, setClearDialogOpen] = useState(false);
  const model = useLobbyProjectModel({ deletedOnly: true });

  return (
    <div className="h-full" style={{ background: "var(--bg-canvas)" }}>
      <PageEntrance>
        <div className="h-full flex flex-col">
          {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent-primary)" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "var(--accent-primary)" }}>
                项目管理
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              回收站
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                {model.deletedProjectCount} 个项目
              </span>
              <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                保留 30 天
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              className="h-8 px-3 rounded-md text-[12px] w-48"
              placeholder="搜索项目"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
              value={model.searchText}
              onChange={(event) => model.setSearchText(event.target.value)}
            />
            <button
              className="h-8 px-4 rounded-md text-[12px] font-medium"
              disabled={model.deletedProjectCount === 0 || model.emptyTrashMutation.isPending}
              style={{
                background: model.deletedProjectCount > 0 ? "var(--accent-danger-soft)" : "var(--bg-surface)",
                color: model.deletedProjectCount > 0 ? "var(--accent-danger)" : "var(--text-tertiary)",
                border: "1px solid var(--line-medium)",
              }}
              type="button"
              onClick={() => setClearDialogOpen(true)}
            >
              {model.emptyTrashMutation.isPending ? "清空中..." : "清空"}
            </button>
            <Link
              className="h-8 px-4 rounded-md text-[12px] font-medium flex items-center"
              href="/workspace/lobby"
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
            >
              返回书架
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto" style={{ scrollbarWidth: "thin", scrollbarColor: "var(--line-medium) transparent" }}>
        <div className="px-6 py-5">
          {model.projectsQuery.isLoading ? (
            <LoadingState />
          ) : model.projectsQuery.error ? (
            <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {getErrorMessage(model.projectsQuery.error)}
            </div>
          ) : model.filteredProjects.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {model.filteredProjects.map((project) => (
                <RecycleBinCard
                  key={project.id}
                  actionMutation={model.actionMutation}
                  project={project}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {isClearDialogOpen ? (
        <RecycleBinClearDialog
          isPending={model.emptyTrashMutation.isPending}
          onClose={() => setClearDialogOpen(false)}
          onConfirm={() =>
            model.emptyTrashMutation.mutate(undefined, {
              onSuccess: () => setClearDialogOpen(false),
            })
          }
          projectCount={model.deletedProjectCount}
        />
      ) : null}
        </div>
    </PageEntrance>
    </div>
  );
}

function RecycleBinCard({
  actionMutation,
  project,
}: {
  actionMutation: ReturnType<typeof useLobbyProjectModel>["actionMutation"];
  project: ProjectSummary;
}) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const isRestoring = actionMutation.isPending && actionMutation.variables?.projectId === project.id && actionMutation.variables?.type === "restore";
  const isDeleting = actionMutation.isPending && actionMutation.variables?.projectId === project.id && actionMutation.variables?.type === "physicalDelete";

  return (
    <>
      <div
        className="rounded-lg p-4 transition-colors hover:brightness-110"
        style={{
          background: "var(--bg-canvas)",
          border: "1px solid var(--line-soft)",
        }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center text-[11px] font-bold flex-shrink-0"
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
            >
              {project.name.charAt(0)}
            </div>
            <span className="text-[13px] font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {project.name}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>
            {project.genre ?? "未定题材"}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--accent-warning-soft)", color: "var(--accent-warning)" }}>
            {project.target_words ? `${(project.target_words / 10000).toFixed(1)}万字` : "未设定"}
          </span>
        </div>

        <p className="mt-2 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          删除于 {formatTrashTime(project.deleted_at)}
        </p>

        <div className="flex gap-2 mt-3">
          <button
            className="h-7 px-3 rounded text-[11px] font-medium"
            disabled={isRestoring || isDeleting}
            style={{ background: "var(--accent-success-soft)", color: "var(--accent-success)" }}
            onClick={() => actionMutation.mutate({ projectId: project.id, type: "restore" })}
            type="button"
          >
            {isRestoring ? "恢复中..." : "恢复"}
          </button>
          <button
            className="h-7 px-3 rounded text-[11px] font-medium"
            disabled={isRestoring || isDeleting}
            style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
            onClick={() => setShowDeleteDialog(true)}
            type="button"
          >
            {isDeleting ? "删除中..." : "彻底删除"}
          </button>
        </div>
      </div>

      {showDeleteDialog ? (
        <DeleteConfirmDialog
          onClose={() => setShowDeleteDialog(false)}
          onConfirm={() => {
            actionMutation.mutate(
              { projectId: project.id, type: "physicalDelete" },
              { onSuccess: () => setShowDeleteDialog(false) },
            );
          }}
          project={project}
        />
      ) : null}
    </>
  );
}

function DeleteConfirmDialog({
  onClose,
  onConfirm,
  project,
}: {
  onClose: () => void;
  onConfirm: () => void;
  project: ProjectSummary;
}) {
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
            <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>{project.name}</p>
          </div>
          <p className="text-[11px]" style={{ color: "var(--accent-danger)" }}>
            删除后无法恢复，所有关联数据将一并清理。
          </p>
        </div>
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid var(--line-soft)" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
            onClick={onConfirm}
            type="button"
          >
            确认删除
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
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

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-12 h-12 rounded-full flex items-center justify-center mb-4" style={{ background: "var(--bg-muted)" }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round">
          <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </div>
      <p className="text-[14px] font-medium" style={{ color: "var(--text-secondary)" }}>回收站为空</p>
      <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>删除的项目会保留 30 天</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin mb-3" style={{ borderColor: "var(--line-medium)", borderTopColor: "transparent" }} />
      <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>加载中...</p>
    </div>
  );
}

function formatTrashTime(value: string | null): string {
  if (!value) return "未知";
  const date = new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
