"use client";

import { ProjectAuditPanel } from "@/features/project-settings/components/project-audit-panel";
import type { ProjectSettingsTab } from "@/features/project-settings/components/project-settings-support";
import { AssistantMcpPanel } from "@/features/settings/components/assistant-mcp-panel";
import { AssistantPreferencesPanel } from "@/features/settings/components/assistant-preferences-panel";
import { AssistantRulesEditor } from "@/features/settings/components/assistant-rules-editor";
import { AssistantSkillsPanel } from "@/features/settings/components/assistant-skills-panel";
import { ProjectSettingEditor } from "@/features/studio/components/project-setting-editor";
import { getErrorMessage } from "@/lib/api/client";
import { checkProjectSetting, getProject } from "@/lib/api/projects";
import styles from "./project-settings-page.module.css";

type ProjectSettingsContentProps = {
  completeness: Awaited<ReturnType<typeof checkProjectSetting>> | undefined;
  eventType: string | null;
  onEventTypeChange: (eventType: string | null) => void;
  onProjectMcpDirtyChange: (isDirty: boolean) => void;
  onProjectPreferencesDirtyChange: (isDirty: boolean) => void;
  onProjectRulesDirtyChange: (isDirty: boolean) => void;
  onProjectSettingDirtyChange: (isDirty: boolean) => void;
  onProjectSkillsDirtyChange: (isDirty: boolean) => void;
  projectError: unknown;
  projectId: string;
  projectLoading: boolean;
  projectSetting: Awaited<ReturnType<typeof getProject>>["project_setting"] | null;
  tab: ProjectSettingsTab;
};

export function ProjectSettingsContent({
  completeness,
  eventType,
  onEventTypeChange,
  onProjectMcpDirtyChange,
  onProjectPreferencesDirtyChange,
  onProjectRulesDirtyChange,
  onProjectSettingDirtyChange,
  onProjectSkillsDirtyChange,
  projectError,
  projectId,
  projectLoading,
  projectSetting,
  tab,
}: Readonly<ProjectSettingsContentProps>) {
  if (tab === "setting" && projectLoading) {
    return (
      <div className={styles.contentCard}>
        <div className={styles.loadingText}>
          <div className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin opacity-50" />
            <span>正在加载项目设定...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.content}>
      {projectError ? (
        <div className={styles.errorCard}>
          <p className={styles.errorText}>{getErrorMessage(projectError)}</p>
        </div>
      ) : null}
      {tab === "setting" && !projectError ? (
        <div className={styles.contentCard}>
          <ProjectSettingEditor
            completeness={completeness}
            initialSetting={projectSetting}
            onDirtyChange={onProjectSettingDirtyChange}
            projectId={projectId}
          />
        </div>
      ) : null}
      {tab === "rules" ? (
        <div className={styles.contentCard}>
          <AssistantRulesEditor
            description="只影响这个项目里的聊天和创作建议。适合写题材方向、风格限制和明确不想要的内容。"
            onDirtyChange={onProjectRulesDirtyChange}
            projectId={projectId}
            scope="project"
            title="项目长期规则"
          />
        </div>
      ) : null}
      {tab === "assistant" ? (
        <div className={styles.contentCard}>
          <AssistantPreferencesPanel
            onDirtyChange={onProjectPreferencesDirtyChange}
            projectId={projectId}
            scope="project"
          />
        </div>
      ) : null}
      {tab === "skills" ? (
        <div className={styles.contentCard}>
          <AssistantSkillsPanel
            onDirtyChange={onProjectSkillsDirtyChange}
            projectId={projectId}
            scope="project"
          />
        </div>
      ) : null}
      {tab === "mcp" ? (
        <div className={styles.contentCard}>
          <AssistantMcpPanel
            onDirtyChange={onProjectMcpDirtyChange}
            projectId={projectId}
            scope="project"
          />
        </div>
      ) : null}
      {tab === "audit" ? (
        <div className={styles.contentCard}>
          <ProjectAuditPanel
            eventType={eventType}
            onEventTypeChange={onEventTypeChange}
            projectId={projectId}
          />
        </div>
      ) : null}
    </div>
  );
}
