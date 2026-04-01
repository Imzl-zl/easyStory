"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import { ProjectSettingsContent } from "@/features/project-settings/components/project-settings-content";
import { ProjectSettingsSidebar } from "@/features/project-settings/components/project-settings-sidebar";
import {
  buildProjectSettingsPathWithParams,
  isValidProjectSettingsTab,
  normalizeProjectAuditEventType,
  resolveProjectSettingsTab,
  type ProjectSettingsTab,
} from "@/features/project-settings/components/project-settings-support";
import { checkProjectSetting, getProject } from "@/lib/api/projects";
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";

type ProjectSettingsPageProps = {
  projectId: string;
};

export function ProjectSettingsPage({ projectId }: ProjectSettingsPageProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [projectMcpDirty, setProjectMcpDirty] = useState(false);
  const [projectPreferencesDirty, setProjectPreferencesDirty] = useState(false);
  const [projectRulesDirty, setProjectRulesDirty] = useState(false);
  const [projectSettingDirty, setProjectSettingDirty] = useState(false);
  const [projectSkillsDirty, setProjectSkillsDirty] = useState(false);
  const routeTab = searchParams.get("tab");
  const routeEvent = searchParams.get("event");
  const currentSearch = searchParams.toString();
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;
  const tab = resolveProjectSettingsTab(routeTab);
  const eventType = normalizeProjectAuditEventType(routeEvent);
  const isDirty = resolveProjectSettingsDirtyState(tab, {
    assistant: projectPreferencesDirty,
    mcp: projectMcpDirty,
    rules: projectRulesDirty,
    setting: projectSettingDirty,
    skills: projectSkillsDirty,
  });
  const navigationGuard = useUnsavedChangesGuard({ currentUrl, isDirty, router });
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const completenessQuery = useQuery({
    queryKey: ["setting-check", projectId],
    queryFn: () => checkProjectSetting(projectId),
  });

  const setParams = useCallback(
    (patches: Record<string, string | null>) => {
      startTransition(() => {
        router.replace(buildProjectSettingsPathWithParams(pathname, currentSearch, patches));
      });
    },
    [currentSearch, pathname, router],
  );

  useEffect(() => {
    const hasInvalidTab = routeTab !== null && !isValidProjectSettingsTab(routeTab);
    const hasUnnormalizedEvent = routeEvent !== eventType;
    if (!hasInvalidTab && !hasUnnormalizedEvent) {
      return;
    }
    setParams({
      event: hasInvalidTab ? null : eventType,
      tab: hasInvalidTab ? null : routeTab,
    });
  }, [eventType, routeEvent, routeTab, setParams]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isDirty) {
        event.preventDefault();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDirty]);

  return (
    <>
      <div className="grid gap-gap-lg grid-cols-[280px_1fr] min-h-[calc(100vh-4rem)] p-card-xl max-w-[1600px] mx-auto">
        <div className="sticky top-6 h-fit max-h-[calc(100vh-4rem)] overflow-y-auto scrollbar-thin animate-[slideInLeft_0.35s_cubic-bezier(0.16,1,0.3,1)]">
          <ProjectSettingsSidebar
            dirtyState={{
              assistant: projectPreferencesDirty,
              mcp: projectMcpDirty,
              rules: projectRulesDirty,
              setting: projectSettingDirty,
              skills: projectSkillsDirty,
              audit: false,
            }}
            isDirty={isDirty}
            isPending={isPending}
            onNavigate={navigationGuard.attemptNavigation}
            onSelectTab={(nextTab) =>
              navigationGuard.attemptNavigation(() => handleSelectTab(nextTab, eventType, setParams))
            }
            projectId={projectId}
            projectName={projectQuery.data?.name ?? "正在加载项目..."}
            projectStatus={projectQuery.data?.status ?? null}
            tab={tab}
          />
        </div>
        <div className="relative flex flex-col min-h-[600px] animate-[fadeIn_0.35s_cubic-bezier(0.16,1,0.3,1)]">
          <ProjectSettingsContent
            completeness={completenessQuery.data}
            eventType={eventType}
            onEventTypeChange={(nextEventType) => setParams({ event: nextEventType, tab: "audit" })}
            onProjectMcpDirtyChange={setProjectMcpDirty}
            onProjectPreferencesDirtyChange={setProjectPreferencesDirty}
            onProjectRulesDirtyChange={setProjectRulesDirty}
            onProjectSettingDirtyChange={setProjectSettingDirty}
            onProjectSkillsDirtyChange={setProjectSkillsDirty}
            projectError={projectQuery.error}
            projectId={projectId}
            projectLoading={projectQuery.isLoading}
            projectSetting={projectQuery.data?.project_setting ?? null}
            tab={tab}
          />
        </div>
      </div>
      <UnsavedChangesDialog
        isOpen={navigationGuard.isConfirmOpen}
        isPending={false}
        onClose={navigationGuard.handleDialogClose}
        onConfirm={navigationGuard.handleDialogConfirm}
      />
    </>
  );
}

function resolveProjectSettingsDirtyState(
  tab: ProjectSettingsTab,
  dirtyState: {
    assistant: boolean;
    mcp: boolean;
    rules: boolean;
    setting: boolean;
    skills: boolean;
  },
) {
  if (tab === "setting") {
    return dirtyState.setting;
  }
  if (tab === "rules") {
    return dirtyState.rules;
  }
  if (tab === "assistant") {
    return dirtyState.assistant;
  }
  if (tab === "skills") {
    return dirtyState.skills;
  }
  if (tab === "mcp") {
    return dirtyState.mcp;
  }
  return false;
}

function handleSelectTab(
  nextTab: ProjectSettingsTab,
  eventType: string | null,
  setParams: (patches: Record<string, string | null>) => void,
) {
  if (nextTab === "setting") {
    setParams({ event: null, tab: null });
    return;
  }
  if (nextTab === "rules") {
    setParams({ event: null, tab: "rules" });
    return;
  }
  if (nextTab === "assistant") {
    setParams({ event: null, tab: "assistant" });
    return;
  }
  if (nextTab === "skills") {
    setParams({ event: null, tab: "skills" });
    return;
  }
  if (nextTab === "mcp") {
    setParams({ event: null, tab: "mcp" });
    return;
  }
  setParams({ event: eventType, tab: "audit" });
}
