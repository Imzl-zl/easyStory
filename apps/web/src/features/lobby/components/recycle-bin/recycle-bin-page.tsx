"use client";

import { useState } from "react";
import Link from "next/link";

import { SectionCard } from "@/components/ui/section-card";
import { useLobbyProjectModel } from "@/features/lobby/components/projects/lobby-project-model";
import { resolveEmptyTrashButtonLabel } from "@/features/lobby/components/projects/lobby-project-support";
import { LobbyProjectShelf } from "@/features/lobby/components/projects/lobby-project-shelf";
import { RecycleBinClearDialog } from "@/features/lobby/components/recycle-bin/recycle-bin-dialogs";

export function RecycleBinPage() {
  const [isClearDialogOpen, setClearDialogOpen] = useState(false);
  const model = useLobbyProjectModel({ deletedOnly: true });

  return (
    <div className="space-y-6">
      <SectionCard
        title="回收站"
        description="已删除项目会保留在回收站，可恢复、彻底删除或手动清空。"
        action={<Link className="ink-button-secondary" href="/workspace/lobby">返回书架</Link>}
      >
        <div className="space-y-5">
          <RecycleBinSummaryCard
            deletedProjectCount={model.deletedProjectCount}
            isPending={model.emptyTrashMutation.isPending}
            onClear={() => setClearDialogOpen(true)}
          />
          <label className="block">
            <span className="label-text">快速搜索</span>
            <input
              className="ink-input"
              placeholder="按项目名过滤"
              value={model.searchText}
              onChange={(event) => model.setSearchText(event.target.value)}
            />
          </label>
          <LobbyProjectShelf
            actionMutation={model.actionMutation}
            deletedOnly
            error={model.projectsQuery.error}
            isLoading={model.projectsQuery.isLoading}
            projects={model.filteredProjects}
            templateNameById={model.templateNameById}
          />
        </div>
      </SectionCard>
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
  );
}

function RecycleBinSummaryCard({
  deletedProjectCount,
  isPending,
  onClear,
}: Readonly<{
  deletedProjectCount: number;
  isPending: boolean;
  onClear: () => void;
}>) {
  return (
    <section className="grid gap-4 rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,250,243,0.88)] p-5 lg:grid-cols-[1fr_auto] lg:items-center">
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">回收站状态</p>
        <h3 className="font-serif text-2xl font-semibold text-[var(--text-primary)]">
          当前共有 {deletedProjectCount} 个已删除项目
        </h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          删除后默认保留 30 天。到期前你可以恢复，也可以立即彻底删除。
        </p>
      </div>
      <button
        className="ink-button-danger"
        disabled={deletedProjectCount === 0 || isPending}
        onClick={onClear}
        type="button"
      >
        {resolveEmptyTrashButtonLabel(isPending)}
      </button>
    </section>
  );
}
