"use client";

import { GuardedLink } from "@/components/ui/guarded-link";
import { StatusBadge } from "@/components/ui/status-badge";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
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
    <div className="sticky top-6 h-fit max-h-[calc(100vh-4rem)] overflow-y-auto rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] p-4 shadow-sm scrollbar-thin">
      <div className="space-y-1 rounded-[18px] bg-[rgba(248,243,235,0.78)] px-4 py-3">
        <h2 className="font-serif text-lg font-semibold text-[var(--text-primary)]">项目设置</h2>
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
          管理项目设定、规则、AI 偏好、Skills、MCP 和操作记录
        </p>
      </div>

      <div className="mt-4 space-y-2 rounded-[18px] bg-[rgba(248,243,235,0.78)] px-4 py-3">
        <p className="text-sm font-medium text-[var(--text-primary)]">{projectName}</p>
        {projectStatus ? (
          <div className="mt-2">
            <StatusBadge status={projectStatus} />
          </div>
        ) : null}
      </div>

      <nav className="mt-4 space-y-1" role="tablist" aria-label="项目设置导航">
        <TabButton
          active={tab === "setting"}
          description="项目基础资料"
          disabled={isPending}
          dirty={dirtyState.setting}
          icon={<SettingsIcon className="w-4 h-4" />}
          label="设定"
          onClick={() => onSelectTab("setting")}
        />
        <TabButton
          active={tab === "rules"}
          description="当前项目的专属要求"
          disabled={isPending}
          dirty={dirtyState.rules}
          icon={<RulesIcon className="w-4 h-4" />}
          label="规则"
          onClick={() => onSelectTab("rules")}
        />
        <TabButton
          active={tab === "assistant"}
          description="这个项目的默认聊天方式"
          disabled={isPending}
          dirty={dirtyState.assistant}
          icon={<AssistantIcon className="w-4 h-4" />}
          label="AI 偏好"
          onClick={() => onSelectTab("assistant")}
        />
        <TabButton
          active={tab === "skills"}
          description="这个项目自己的长期写法"
          disabled={isPending}
          dirty={dirtyState.skills}
          icon={<SkillsIcon className="w-4 h-4" />}
          label="Skills"
          onClick={() => onSelectTab("skills")}
        />
        <TabButton
          active={tab === "mcp"}
          description="这个项目自己的外部工具"
          disabled={isPending}
          dirty={dirtyState.mcp}
          icon={<McpIcon className="w-4 h-4" />}
          label="MCP"
          onClick={() => onSelectTab("mcp")}
        />
        <TabButton
          active={tab === "audit"}
          description="查看最近操作记录"
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
          href={`/workspace/project/${projectId}/studio?panel=setting`}
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

      <div className="mt-4">
        <PreparationStatusPanel projectId={projectId} />
      </div>
    </div>
  );
}

function TabButton({
  active,
  description,
  disabled,
  dirty,
  icon,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  description: string;
  disabled: boolean;
  dirty: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={`relative flex flex-col items-stretch gap-1 w-full px-3.5 py-3 border-none rounded-[var(--radius-md)] bg-transparent text-[var(--text-primary)] cursor-pointer text-left transition-colors outline-none hover:bg-[var(--bg-surface-hover)] ${
        active ? "bg-[var(--bg-surface-active)] before:content-[''] before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:bg-[var(--accent-primary)] before:rounded-r-[2px]" : ""
      }`}
      disabled={disabled}
      onClick={onClick}
      role="tab"
      aria-selected={active}
      tabIndex={active ? 0 : -1}
      type="button"
    >
      <div className="flex items-center gap-2">
        <span className="text-[var(--text-secondary)]">{icon}</span>
        <span className="text-sm font-medium">{label}</span>
        {dirty && (
          <span 
            className="ml-auto w-2 h-2 rounded-full bg-[var(--accent-warning)]" 
            aria-label="有未保存的更改" 
          />
        )}
      </div>
      <span className="text-[12px] leading-5 text-[var(--text-secondary)] ml-6">{description}</span>
    </button>
  );
}
