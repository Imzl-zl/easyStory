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
    return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载项目设定...</div>;
  }

  return (
    <div className="space-y-4">
      {projectError ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {getErrorMessage(projectError)}
        </div>
      ) : null}
      {tab === "setting" && !projectError ? (
        <ProjectSettingEditor
          completeness={completeness}
          initialSetting={projectSetting}
          onDirtyChange={onProjectSettingDirtyChange}
          projectId={projectId}
        />
      ) : null}
      {tab === "rules" ? (
        <AssistantRulesEditor
          description="只影响这个项目里的聊天和创作建议。适合写题材方向、风格限制和明确不想要的内容。"
          onDirtyChange={onProjectRulesDirtyChange}
          projectId={projectId}
          scope="project"
          title="项目长期规则"
        />
      ) : null}
      {tab === "assistant" ? (
        <AssistantPreferencesPanel
          onDirtyChange={onProjectPreferencesDirtyChange}
          projectId={projectId}
          scope="project"
        />
      ) : null}
      {tab === "skills" ? (
        <AssistantSkillsPanel
          onDirtyChange={onProjectSkillsDirtyChange}
          projectId={projectId}
          scope="project"
        />
      ) : null}
      {tab === "mcp" ? (
        <AssistantMcpPanel
          onDirtyChange={onProjectMcpDirtyChange}
          projectId={projectId}
          scope="project"
        />
      ) : null}
      {tab === "audit" ? (
        <ProjectAuditPanel
          eventType={eventType}
          onEventTypeChange={onEventTypeChange}
          projectId={projectId}
        />
      ) : null}
    </div>
  );
}
