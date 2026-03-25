"use client";

import Link from "next/link";

import { SectionCard } from "@/components/ui/section-card";
import { useLobbyProjectModel } from "@/features/lobby/components/lobby-project-model";
import { LobbyProjectShelf } from "@/features/lobby/components/lobby-project-shelf";

export function RecycleBinPage() {
  const model = useLobbyProjectModel({ deletedOnly: true });

  return (
    <div className="space-y-6">
      <SectionCard
        title="Recycle Bin"
        description="回收站只处理已删除项目的浏览与恢复，不暴露永久删除。"
        action={<Link className="ink-button-secondary" href="/workspace/lobby">返回 Lobby</Link>}
      >
        <div className="space-y-5">
          {model.feedback ? (
            <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
              {model.feedback}
            </div>
          ) : null}
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
    </div>
  );
}
