"use client";

import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
import { ProjectSettingsTabButton } from "@/features/project-settings/components/project-settings-tab-button";
import type { ProjectSettingsTab } from "@/features/project-settings/components/project-settings-support";

type ProjectSettingsSidebarProps = {
  isDirty: boolean;
  isPending: boolean;
  onNavigate: (onConfirm: () => void) => void;
  onSelectTab: (tab: ProjectSettingsTab) => void;
  projectId: string;
  projectName: string;
  projectStatus: string | null;
  tab: ProjectSettingsTab;
};

export function ProjectSettingsSidebar({
  isDirty,
  isPending,
  onNavigate,
  onSelectTab,
  projectId,
  projectName,
  projectStatus,
  tab,
}: Readonly<ProjectSettingsSidebarProps>) {
  return (
    <aside className="space-y-6 xl:sticky xl:top-6 xl:self-start">
      <SectionCard
        title="项目设置"
        description="管理项目设定、规则、AI 偏好、Skills、MCP 和操作记录。"
        action={
          <GuardedLink
            className="ink-button-secondary"
            href="/workspace/lobby"
            isDirty={isDirty}
            onNavigate={onNavigate}
          >
            返回项目大厅
          </GuardedLink>
        }
      >
        <div className="space-y-4">
          <div className="panel-muted space-y-2 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent-ink)]">项目</p>
            <h1 className="font-serif text-2xl font-semibold text-[var(--text-primary)]">{projectName}</h1>
            {projectStatus ? <StatusBadge status={projectStatus} /> : null}
          </div>
          <div className="space-y-2">
            <ProjectSettingsTabButton
              active={tab === "setting"}
              description="项目基础资料"
              disabled={isPending}
              label="设定"
              onClick={() => onSelectTab("setting")}
            />
            <ProjectSettingsTabButton
              active={tab === "rules"}
              description="当前项目的专属要求"
              disabled={isPending}
              label="规则"
              onClick={() => onSelectTab("rules")}
            />
            <ProjectSettingsTabButton
              active={tab === "assistant"}
              description="这个项目的默认聊天方式"
              disabled={isPending}
              label="AI 偏好"
              onClick={() => onSelectTab("assistant")}
            />
            <ProjectSettingsTabButton
              active={tab === "skills"}
              description="这个项目自己的长期写法"
              disabled={isPending}
              label="Skills"
              onClick={() => onSelectTab("skills")}
            />
            <ProjectSettingsTabButton
              active={tab === "mcp"}
              description="这个项目自己的外部工具"
              disabled={isPending}
              label="MCP"
              onClick={() => onSelectTab("mcp")}
            />
            <ProjectSettingsTabButton
              active={tab === "audit"}
              description="查看最近操作记录"
              disabled={isPending}
              label="审计"
              onClick={() => onSelectTab("audit")}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <GuardedLink
              className="ink-button-secondary"
              href={`/workspace/project/${projectId}/studio?panel=setting`}
              isDirty={isDirty}
              onNavigate={onNavigate}
            >
              进入编辑器
            </GuardedLink>
            <GuardedLink
              className="ink-button-secondary"
              href={`/workspace/project/${projectId}/engine`}
              isDirty={isDirty}
              onNavigate={onNavigate}
            >
              打开执行器
            </GuardedLink>
            <GuardedLink
              className="ink-button-secondary"
              href={`/workspace/lobby/settings?tab=credentials&scope=project&project=${projectId}&sub=list`}
              isDirty={isDirty}
              onNavigate={onNavigate}
            >
              项目凭证
            </GuardedLink>
          </div>
        </div>
      </SectionCard>
      <PreparationStatusPanel projectId={projectId} />
    </aside>
  );
}
