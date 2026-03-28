"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
import { ProjectAuditPanel } from "@/features/project-settings/components/project-audit-panel";
import { ProjectSettingsTabButton } from "@/features/project-settings/components/project-settings-tab-button";
import {
  buildProjectSettingsPathWithParams,
  isValidProjectSettingsTab,
  normalizeProjectAuditEventType,
  resolveProjectSettingsTab,
  type ProjectSettingsTab,
} from "@/features/project-settings/components/project-settings-support";
import { AssistantRulesEditor } from "@/features/settings/components/assistant-rules-editor";
import { ProjectSettingEditor } from "@/features/studio/components/project-setting-editor";
import { getErrorMessage } from "@/lib/api/client";
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
  const [projectRulesDirty, setProjectRulesDirty] = useState(false);
  const [projectSettingDirty, setProjectSettingDirty] = useState(false);
  const routeTab = searchParams.get("tab");
  const routeEvent = searchParams.get("event");
  const currentSearch = searchParams.toString();
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;
  const tab = resolveProjectSettingsTab(routeTab);
  const eventType = normalizeProjectAuditEventType(routeEvent);
  const isDirty = tab === "setting" ? projectSettingDirty : tab === "rules" ? projectRulesDirty : false;
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

  return (
    <>
      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <ProjectSettingsSidebar
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
        <ProjectSettingsContent
          completeness={completenessQuery.data}
          eventType={eventType}
          projectError={projectQuery.error}
          projectLoading={projectQuery.isLoading}
          projectId={projectId}
          projectSetting={projectQuery.data?.project_setting ?? null}
          tab={tab}
          onEventTypeChange={(nextEventType) => setParams({ event: nextEventType, tab: "audit" })}
          onProjectRulesDirtyChange={setProjectRulesDirty}
          onProjectSettingDirtyChange={setProjectSettingDirty}
        />
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

function ProjectSettingsSidebar({
  isDirty,
  isPending,
  onNavigate,
  onSelectTab,
  projectId,
  projectName,
  projectStatus,
  tab,
}: Readonly<{
  isDirty: boolean;
  isPending: boolean;
  onNavigate: (onConfirm: () => void) => void;
  onSelectTab: (tab: ProjectSettingsTab) => void;
  projectId: string;
  projectName: string;
  projectStatus: string | null;
  tab: ProjectSettingsTab;
}>) {
  return (
    <aside className="space-y-6 xl:sticky xl:top-6 xl:self-start">
      <SectionCard
        title="项目设置"
        description="管理项目设定、项目规则和操作记录。"
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

function ProjectSettingsContent({
  completeness,
  eventType,
  projectError,
  projectLoading,
  projectId,
  projectSetting,
  tab,
  onEventTypeChange,
  onProjectRulesDirtyChange,
  onProjectSettingDirtyChange,
}: Readonly<{
  completeness: Awaited<ReturnType<typeof checkProjectSetting>> | undefined;
  eventType: string | null;
  projectError: unknown;
  projectLoading: boolean;
  projectId: string;
  projectSetting: Awaited<ReturnType<typeof getProject>>["project_setting"] | null;
  tab: ProjectSettingsTab;
  onEventTypeChange: (eventType: string | null) => void;
  onProjectRulesDirtyChange: (isDirty: boolean) => void;
  onProjectSettingDirtyChange: (isDirty: boolean) => void;
}>) {
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
  setParams({ event: eventType, tab: "audit" });
}
