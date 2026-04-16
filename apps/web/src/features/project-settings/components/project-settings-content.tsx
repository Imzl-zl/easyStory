"use client";

import { ProjectAuditPanel } from "@/features/project-settings/components/project-audit-panel";
import { ProjectSettingSummaryPanel } from "@/features/project-settings/components/project-setting-summary-panel";
import type { ProjectSettingsTab } from "@/features/project-settings/components/project-settings-support";
import { AssistantMcpPanel } from "@/features/settings/components/assistant/mcp/assistant-mcp-panel";
import { AssistantPreferencesPanel } from "@/features/settings/components/assistant/preferences/assistant-preferences-panel";
import { AssistantRulesEditor } from "@/features/settings/components/assistant/rules/assistant-rules-editor";
import { AssistantSkillsPanel } from "@/features/settings/components/assistant/skills/assistant-skills-panel";
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
    return (
      <div className="rounded-2xl bg-surface shadow-sm p-6">
        <div className="flex items-center justify-center gap-2 px-4 py-8 text-sm text-text-secondary">
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin opacity-50" />
          <span>正在加载项目摘要...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {projectError ? (
        <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
          <p>{getErrorMessage(projectError)}</p>
        </div>
      ) : null}
      {tab === "setting" && !projectError ? (
        <div className="rounded-2xl bg-surface shadow-sm p-6">
          <ProjectSettingSummaryPanel
            completeness={completeness}
            onDirtyChange={onProjectSettingDirtyChange}
            projectId={projectId}
            projectSetting={projectSetting}
          />
        </div>
      ) : null}
      {tab === "rules" ? (
        <div className="rounded-2xl bg-surface shadow-sm p-6">
          <AssistantRulesEditor
            onDirtyChange={onProjectRulesDirtyChange}
            projectId={projectId}
            scope="project"
            title="项目长期规则"
          />
        </div>
      ) : null}
      {tab === "assistant" ? (
        <div className="rounded-2xl bg-surface shadow-sm p-6">
          <AssistantPreferencesPanel
            onDirtyChange={onProjectPreferencesDirtyChange}
            projectId={projectId}
            scope="project"
          />
        </div>
      ) : null}
      {tab === "skills" ? (
        <div className="rounded-2xl bg-surface shadow-sm p-6">
          <AssistantSkillsPanel
            onDirtyChange={onProjectSkillsDirtyChange}
            projectId={projectId}
            scope="project"
          />
        </div>
      ) : null}
      {tab === "mcp" ? (
        <div className="rounded-2xl bg-surface shadow-sm p-6">
          <AssistantMcpPanel
            onDirtyChange={onProjectMcpDirtyChange}
            projectId={projectId}
            scope="project"
          />
        </div>
      ) : null}
      {tab === "audit" ? (
        <div className="rounded-2xl bg-surface shadow-sm p-6">
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
