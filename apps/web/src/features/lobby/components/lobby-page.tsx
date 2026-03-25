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
        title="Lobby"
        description="项目书架只负责浏览和筛选；新建、模板管理、回收站和设置都走独立子视图。"
        action={<LobbyToolbar />}
      >
        <div className="grid gap-6 xl:grid-cols-[0.72fr_1.28fr]">
          <div className="space-y-4">
            <LobbyEntryCard
              feedback={model.feedback}
              templateCount={model.templateCount}
              templatePreviewNames={model.templatePreviewNames}
              templatesError={model.templatesQuery.error ? getErrorMessage(model.templatesQuery.error) : null}
              templatesLoading={model.templatesQuery.isLoading}
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
    <div className="flex flex-wrap gap-2">
      <Link className="ink-button-secondary" href="/workspace/lobby/settings?tab=credentials&sub=list">
        全局设置
      </Link>
      <Link className="ink-button-secondary" href="/workspace/lobby/config-registry?type=skills">
        配置中心
      </Link>
      <Link className="ink-button-secondary" href="/workspace/lobby/recycle-bin">
        回收站
      </Link>
    </div>
  );
}
