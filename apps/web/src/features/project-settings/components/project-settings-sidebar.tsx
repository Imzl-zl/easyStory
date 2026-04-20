"use client";

import { GuardedLink } from "@/components/ui/guarded-link";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  AuditIcon,
  AssistantIcon,
  EngineIcon,
  KeyIcon,
  McpIcon,
  RulesIcon,
  SettingsIcon,
  SkillsIcon,
  StudioIcon,
} from "@/features/project-settings/components/project-settings-icons";
import type { ProjectSettingsTab } from "@/features/project-settings/components/project-settings-support";

type ProjectSettingsSidebarProps = {
  dirtyState: Record<ProjectSettingsTab, boolean>;
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
  dirtyState,
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
    <div className="sticky top-6 h-fit max-h-[calc(100vh-4rem)] overflow-y-auto rounded-3xl bg-glass shadow-glass backdrop-blur-lg p-4 scrollbar-thin">
      <div className="space-y-1 rounded-2xl bg-accent-soft px-4 py-3">
        <h2 className="font-serif text-lg font-semibold text-text-primary">项目设置</h2>
      </div>

      <div className="mt-4 space-y-2 rounded-2xl bg-surface-hover px-4 py-3">
        <p className="text-sm font-medium text-text-primary">{projectName}</p>
        {projectStatus ? (
          <div className="mt-2">
            <StatusBadge status={projectStatus} />
          </div>
        ) : null}
      </div>

      <nav className="mt-4 space-y-1" role="tablist" aria-label="项目设置导航">
        <TabButton
          active={tab === "brief"}
          disabled={isPending}
          dirty={dirtyState.brief}
          icon={<SettingsIcon className="w-4 h-4" />}
          label="摘要"
          onClick={() => onSelectTab("brief")}
        />
        <TabButton
          active={tab === "rules"}
          disabled={isPending}
          dirty={dirtyState.rules}
          icon={<RulesIcon className="w-4 h-4" />}
          label="规则"
          onClick={() => onSelectTab("rules")}
        />
        <TabButton
          active={tab === "assistant"}
          disabled={isPending}
          dirty={dirtyState.assistant}
          icon={<AssistantIcon className="w-4 h-4" />}
          label="AI 偏好"
          onClick={() => onSelectTab("assistant")}
        />
        <TabButton
          active={tab === "skills"}
          disabled={isPending}
          dirty={dirtyState.skills}
          icon={<SkillsIcon className="w-4 h-4" />}
          label="Skills"
          onClick={() => onSelectTab("skills")}
        />
        <TabButton
          active={tab === "mcp"}
          disabled={isPending}
          dirty={dirtyState.mcp}
          icon={<McpIcon className="w-4 h-4" />}
          label="MCP"
          onClick={() => onSelectTab("mcp")}
        />
        <TabButton
          active={tab === "audit"}
          disabled={isPending}
          dirty={dirtyState.audit}
          icon={<AuditIcon className="w-4 h-4" />}
          label="审计"
          onClick={() => onSelectTab("audit")}
        />
      </nav>

      <div className="mt-4 space-y-2">
        <GuardedLink
          className="ink-link-button w-full justify-center"
          href={`/workspace/project/${projectId}/studio?panel=overview&doc=${encodeURIComponent("项目说明.md")}`}
          isDirty={isDirty}
          onNavigate={onNavigate}
        >
          <StudioIcon className="w-3.5 h-3.5" />
          进入编辑器
        </GuardedLink>
        <GuardedLink
          className="ink-link-button w-full justify-center"
          href={`/workspace/project/${projectId}/engine`}
          isDirty={isDirty}
          onNavigate={onNavigate}
        >
          <EngineIcon className="w-3.5 h-3.5" />
          打开执行器
        </GuardedLink>
        <GuardedLink
          className="ink-link-button w-full justify-center"
          href={`/workspace/lobby/settings?tab=credentials&scope=project&project=${projectId}&sub=list`}
          isDirty={isDirty}
          onNavigate={onNavigate}
        >
          <KeyIcon className="w-3.5 h-3.5" />
          项目凭证
        </GuardedLink>
      </div>
    </div>
  );
}

function TabButton({
  active,
  disabled,
  dirty,
  icon,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  disabled: boolean;
  dirty: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={`relative flex items-center gap-2 w-full px-3.5 py-3 border-none rounded-2xl bg-transparent text-text-primary cursor-pointer text-left transition-colors duration-fast outline-none hover:bg-surface-hover ${
        active ? "bg-accent-soft before:content-[''] before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:bg-accent-primary before:rounded-r-sm" : ""
      }`}
      disabled={disabled}
      onClick={onClick}
      role="tab"
      aria-selected={active}
      tabIndex={active ? 0 : -1}
      type="button"
    >
      <span className="text-text-secondary">{icon}</span>
      <span className="text-sm font-medium">{label}</span>
      {dirty && (
        <span
          className="ml-auto w-2 h-2 rounded-full bg-accent-warning"
          aria-label="有未保存的更改"
        />
      )}
    </button>
  );
}
