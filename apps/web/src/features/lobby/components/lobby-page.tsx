"use client";

import Link from "next/link";

import { SectionCard } from "@/components/ui/section-card";
import { LobbyEntryCard } from "@/features/lobby/components/lobby-entry-card";
import { useLobbyProjectModel } from "@/features/lobby/components/lobby-project-model";
import { LobbyProjectShelf } from "@/features/lobby/components/lobby-project-shelf";
import { getErrorMessage } from "@/lib/api/client";

export function LobbyPage() {
  const model = useLobbyProjectModel({ deletedOnly: false });

  return (
    <div className="space-y-6">
      <SectionCard
        title="项目大厅"
        description="查看项目、继续创作或新建项目。"
        action={<LobbyToolbar />}
      >
        <div className="grid gap-6 xl:grid-cols-[0.72fr_1.28fr]">
          <div className="space-y-4">
            <LobbyEntryCard
              templateCount={model.templateCount}
              templatePreviewNames={model.templatePreviewNames}
              templatesError={model.templatesQuery.error ? getErrorMessage(model.templatesQuery.error) : null}
              templatesLoading={model.templatesQuery.isLoading}
            />
            <label className="block">
              <span className="label-text">搜索项目</span>
              <input
                className="ink-input"
                placeholder="按项目名称搜索"
                value={model.searchText}
                onChange={(event) => model.setSearchText(event.target.value)}
              />
            </label>
          </div>
          <LobbyProjectShelf
            actionMutation={model.actionMutation}
            deletedOnly={false}
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

function LobbyToolbar() {
  return (
    <div className="flex flex-wrap items-center justify-end gap-2.5">
      <Link className="ink-button-secondary h-9 px-4 text-[13px]" href="/workspace/lobby/settings?tab=assistant">
        AI 设置
      </Link>
      <Link className="ink-button-secondary h-9 px-4 text-[13px]" href="/workspace/lobby/recycle-bin">
        回收站
      </Link>
      <Link className="ink-button-secondary h-9 px-4 text-[13px]" href="/workspace/lobby/config-registry?type=skills">
        系统配置
      </Link>
    </div>
  );
}
