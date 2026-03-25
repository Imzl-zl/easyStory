"use client";

import { useCallback, useEffect, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { SectionCard } from "@/components/ui/section-card";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
import { ProjectAuditPanel } from "@/features/project-settings/components/project-audit-panel";
import {
  buildProjectSettingsPathWithParams,
  isValidProjectSettingsTab,
  normalizeProjectAuditEventType,
  resolveProjectSettingsTab,
  type ProjectSettingsTab,
} from "@/features/project-settings/components/project-settings-support";
import { ProjectSettingEditor } from "@/features/studio/components/project-setting-editor";
import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api/client";
import { checkProjectSetting, getProject } from "@/lib/api/projects";

type ProjectSettingsPageProps = {
  projectId: string;
};

export function ProjectSettingsPage({ projectId }: ProjectSettingsPageProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const routeTab = searchParams.get("tab");
  const routeEvent = searchParams.get("event");
  const currentSearch = searchParams.toString();
  const tab = resolveProjectSettingsTab(routeTab);
  const eventType = normalizeProjectAuditEventType(routeEvent);
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
    <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
      <ProjectSettingsSidebar
        isPending={isPending}
        onSelectTab={(nextTab) => handleSelectTab(nextTab, eventType, setParams)}
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
      />
    </div>
  );
}

function ProjectSettingsSidebar({
  isPending,
  onSelectTab,
  projectId,
  projectName,
  projectStatus,
  tab,
}: Readonly<{
  isPending: boolean;
  onSelectTab: (tab: ProjectSettingsTab) => void;
  projectId: string;
  projectName: string;
  projectStatus: string | null;
  tab: ProjectSettingsTab;
}>) {
  return (
    <aside className="space-y-6">
      <SectionCard
        title="项目设置"
        description="调整项目设定，查看操作记录。"
        action={<Link className="ink-button-secondary" href="/workspace/lobby">返回项目大厅</Link>}
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
              disabled={isPending}
              label="设定"
              onClick={() => onSelectTab("setting")}
            />
            <ProjectSettingsTabButton
              active={tab === "audit"}
              disabled={isPending}
              label="审计"
              onClick={() => onSelectTab("audit")}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="ink-button-secondary" href={`/workspace/project/${projectId}/studio?panel=setting`}>
              进入 Studio
            </Link>
            <Link className="ink-button-secondary" href={`/workspace/project/${projectId}/engine`}>
              打开 Engine
            </Link>
            <Link
              className="ink-button-secondary"
              href={`/workspace/lobby/settings?tab=credentials&scope=project&project=${projectId}&sub=list`}
            >
              项目凭证
            </Link>
          </div>
        </div>
      </SectionCard>
      <PreparationStatusPanel projectId={projectId} />
    </aside>
  );
}

function ProjectSettingsTabButton({
  active,
  disabled,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  disabled: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className="ink-tab w-full justify-between"
      data-active={active}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span>{label}</span>
      <span className="text-xs uppercase tracking-[0.16em]">标签</span>
    </button>
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
}: Readonly<{
  completeness: Awaited<ReturnType<typeof checkProjectSetting>> | undefined;
  eventType: string | null;
  projectError: unknown;
  projectLoading: boolean;
  projectId: string;
  projectSetting: Awaited<ReturnType<typeof getProject>>["project_setting"] | null;
  tab: ProjectSettingsTab;
  onEventTypeChange: (eventType: string | null) => void;
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
          projectId={projectId}
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
  setParams({ event: eventType, tab: "audit" });
}
