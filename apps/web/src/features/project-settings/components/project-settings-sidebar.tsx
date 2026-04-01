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
import styles from "./project-settings-page.module.css";

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
    <div className={styles.sidebarCard}>
      <div className={styles.sidebarHeader}>
        <h2 className={styles.sidebarTitle}>项目设置</h2>
        <p className={styles.sidebarDescription}>
          管理项目设定、规则、AI 偏好、Skills、MCP 和操作记录
        </p>
      </div>

      <div className={styles.projectInfo}>
        <p className={styles.projectName}>{projectName}</p>
        {projectStatus ? (
          <div className={styles.projectStatus}>
            <StatusBadge status={projectStatus} />
          </div>
        ) : null}
      </div>

      <nav className={styles.tabList} role="tablist" aria-label="项目设置导航">
        <TabButton
          active={tab === "setting"}
          description="项目基础资料"
          disabled={isPending}
          icon={<SettingsIcon className="w-4 h-4" />}
          label="设定"
          onClick={() => onSelectTab("setting")}
        />
        <TabButton
          active={tab === "rules"}
          description="当前项目的专属要求"
          disabled={isPending}
          icon={<RulesIcon className="w-4 h-4" />}
          label="规则"
          onClick={() => onSelectTab("rules")}
        />
        <TabButton
          active={tab === "assistant"}
          description="这个项目的默认聊天方式"
          disabled={isPending}
          icon={<AssistantIcon className="w-4 h-4" />}
          label="AI 偏好"
          onClick={() => onSelectTab("assistant")}
        />
        <TabButton
          active={tab === "skills"}
          description="这个项目自己的长期写法"
          disabled={isPending}
          icon={<SkillsIcon className="w-4 h-4" />}
          label="Skills"
          onClick={() => onSelectTab("skills")}
        />
        <TabButton
          active={tab === "mcp"}
          description="这个项目自己的外部工具"
          disabled={isPending}
          icon={<McpIcon className="w-4 h-4" />}
          label="MCP"
          onClick={() => onSelectTab("mcp")}
        />
        <TabButton
          active={tab === "audit"}
          description="查看最近操作记录"
          disabled={isPending}
          icon={<AuditIcon className="w-4 h-4" />}
          label="审计"
          onClick={() => onSelectTab("audit")}
        />
      </nav>

      <div className={styles.actionGroup}>
        <GuardedLink
          className={styles.actionButton}
          href={`/workspace/project/${projectId}/studio?panel=setting`}
          isDirty={isDirty}
          onNavigate={onNavigate}
        >
          <StudioIcon className="w-3.5 h-3.5" />
          进入编辑器
        </GuardedLink>
        <GuardedLink
          className={styles.actionButton}
          href={`/workspace/project/${projectId}/engine`}
          isDirty={isDirty}
          onNavigate={onNavigate}
        >
          <EngineIcon className="w-3.5 h-3.5" />
          打开执行器
        </GuardedLink>
        <GuardedLink
          className={styles.actionButton}
          href={`/workspace/lobby/settings?tab=credentials&scope=project&project=${projectId}&sub=list`}
          isDirty={isDirty}
          onNavigate={onNavigate}
        >
          <KeyIcon className="w-3.5 h-3.5" />
          项目凭证
        </GuardedLink>
      </div>

      <PreparationStatusPanel projectId={projectId} />
    </div>
  );
}

function TabButton({
  active,
  description,
  disabled,
  icon,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  description: string;
  disabled: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={`${styles.tabButton} ${active ? styles.tabButtonActive : ""}`}
      disabled={disabled}
      onClick={onClick}
      role="tab"
      aria-selected={active}
      tabIndex={active ? 0 : -1}
      type="button"
    >
      <div className={styles.tabButtonRow}>
        <span className={styles.tabButtonIcon}>{icon}</span>
        <span className={styles.tabLabel}>{label}</span>
      </div>
      <span className={styles.tabButtonDescriptionIndented}>{description}</span>
    </button>
  );
}
