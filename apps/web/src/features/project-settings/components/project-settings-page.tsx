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
import { getProject } from "@/lib/api/projects";
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
  const [projectRulesDirty, setProjectRulesDirty] = useState(false);
  const [projectBriefDirty, setProjectBriefDirty] = useState(false);
  const [projectSkillsDirty, setProjectSkillsDirty] = useState(false);
  const routeTab = searchParams.get("tab");
  const routeEvent = searchParams.get("event");
  const currentSearch = searchParams.toString();
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;
  const tab = resolveProjectSettingsTab(routeTab);
  const eventType = normalizeProjectAuditEventType(routeEvent);
  const isDirty = resolveProjectSettingsDirtyState(tab, {
    brief: projectBriefDirty,
    mcp: projectMcpDirty,
    rules: projectRulesDirty,
    skills: projectSkillsDirty,
  });
  const navigationGuard = useUnsavedChangesGuard({ currentUrl, isDirty, router });
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
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
      <div className="grid gap-gap-lg grid-cols-1 lg:grid-cols-[280px_1fr] min-h-[calc(100vh-4rem)] p-card-xl max-w-[1600px] mx-auto">
        <div className="h-fit animate-[slideInLeft_0.35s_cubic-bezier(0.16,1,0.3,1)]">
          <ProjectSettingsSidebar
            dirtyState={{
              brief: projectBriefDirty,
              mcp: projectMcpDirty,
              rules: projectRulesDirty,
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
        <div className="relative flex flex-col min-h-[600px] animate-[fadeIn_0.35s_cubic-bezier(0.16,1,0.3,1)] max-w-3xl w-full mx-auto pb-24">
          <ProjectSettingsContent
            eventType={eventType}
            onEventTypeChange={(nextEventType) => setParams({ event: nextEventType, tab: "audit" })}
            onProjectMcpDirtyChange={setProjectMcpDirty}
            onProjectRulesDirtyChange={setProjectRulesDirty}
            onProjectBriefDirtyChange={setProjectBriefDirty}
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
    brief: boolean;
    mcp: boolean;
    rules: boolean;
    skills: boolean;
  },
) {
  if (tab === "brief") {
    return dirtyState.brief;
  }
  if (tab === "rules") {
    return dirtyState.rules;
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
  if (nextTab === "brief") {
    setParams({ event: null, tab: "brief" });
    return;
  }
  if (nextTab === "rules") {
    setParams({ event: null, tab: null });
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
