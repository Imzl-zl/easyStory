"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
import { ProjectSettingField } from "@/features/studio/components/project-setting-editor-field";
import { ProjectSettingImpactPanel } from "@/features/studio/components/project-setting-impact-panel";
import {
  buildSettingIssueSummary,
  isProjectSettingDirty,
  buildSettingSaveFeedback,
  EMPTY_SETTING,
  invalidateProjectSettingQueries,
} from "@/features/studio/components/project-setting-editor-support";
import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api/client";
import { checkProjectSetting, updateProjectSetting } from "@/lib/api/projects";
import type {
  ProjectSetting,
  ProjectSettingImpactSummary,
  SettingCompletenessResult,
} from "@/lib/api/types";

type ProjectSettingEditorProps = {
  completeness?: SettingCompletenessResult;
  initialSetting: ProjectSetting | null;
  onDirtyChange?: (isDirty: boolean) => void;
  projectId: string;
};

export function ProjectSettingEditor({
  projectId,
  initialSetting,
  completeness,
  onDirtyChange,
}: ProjectSettingEditorProps) {
  const formKey = JSON.stringify(initialSetting ?? EMPTY_SETTING);
  const [lastImpactState, setLastImpactState] = useState<{
    impact: ProjectSettingImpactSummary | null;
    projectId: string;
  }>({
    projectId,
    impact: null,
  });
  const lastImpact = lastImpactState.projectId === projectId ? lastImpactState.impact : null;

  return (
    <ProjectSettingEditorForm
      key={formKey}
      completeness={completeness}
      initialSetting={initialSetting ?? EMPTY_SETTING}
      lastImpact={lastImpact}
      onImpactChange={(impact) => setLastImpactState({ projectId, impact })}
      onDirtyChange={onDirtyChange}
      projectId={projectId}
    />
  );
}

function ProjectSettingEditorForm({
  projectId,
  initialSetting,
  completeness,
  lastImpact,
  onImpactChange,
  onDirtyChange,
}: {
  projectId: string;
  initialSetting: ProjectSetting;
  completeness?: SettingCompletenessResult;
  lastImpact: ProjectSettingImpactSummary | null;
  onImpactChange: (impact: ProjectSettingImpactSummary | null) => void;
  onDirtyChange?: (isDirty: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [setting, setSetting] = useState<ProjectSetting>(initialSetting);
  const isDirty = isProjectSettingDirty(setting, initialSetting);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  const saveMutation = useMutation({
    mutationFn: () => updateProjectSetting(projectId, setting),
    onSuccess: (result) => {
      const message = buildSettingSaveFeedback(result.impact);
      onImpactChange(result.impact);
      showAppNotice({
        content: message,
        title: "项目设定",
        tone: "success",
      });
      invalidateProjectSettingQueries(queryClient, projectId, result.impact);
    },
    onError: (error) => {
      onImpactChange(null);
      showAppNotice({
        content: getErrorMessage(error),
        title: "项目设定",
        tone: "danger",
      });
    },
  });

  const checkMutation = useMutation({
    mutationFn: () => checkProjectSetting(projectId),
    onSuccess: (result) => {
      showAppNotice({
        content: "完整度检查已完成。",
        title: "项目设定",
        tone: "success",
      });
      queryClient.setQueryData(["setting-check", projectId], result);
      queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "项目设定",
        tone: "danger",
      }),
  });

  const issueSummary = buildSettingIssueSummary(completeness);

  return (
    <SectionCard
      title="项目设定"
      description="设定故事的基本信息与创作方向。"
      action={
        <div className="flex flex-wrap gap-2">
          <button
            className="ink-button-secondary"
            disabled={checkMutation.isPending}
            onClick={() => checkMutation.mutate()}
          >
            {checkMutation.isPending ? "检查中..." : "完整度检查"}
          </button>
          <button
            className="ink-button"
            disabled={saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending ? "保存中..." : "保存设定"}
          </button>
        </div>
      }
    >
      <div className="space-y-12">
        <div className="panel-muted flex flex-wrap items-start justify-between gap-4 p-5">
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-[var(--text-secondary)]">设定完整度</p>
            <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{issueSummary}</p>
          </div>
          <StatusBadge status={completeness?.status ?? "draft"} label={completeness?.status ?? "未检查"} />
        </div>

        <fieldset className="border border-[var(--line-soft)] rounded-[var(--radius-lg)] p-7 m-0 bg-gradient-to-br from-[var(--bg-surface)] to-[rgba(255,255,255,0.95)] transition-all relative">
          <legend className="text-[0.75rem] font-semibold text-[var(--text-secondary)] px-2 ml-2 tracking-[0.08em] uppercase">基本信息</legend>
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
            <ProjectSettingField label="题材">
              <input
                className="ink-input"
                value={setting.genre ?? ""}
                onChange={(event) => setSetting((current) => ({ ...current, genre: event.target.value }))}
              />
            </ProjectSettingField>
            <ProjectSettingField label="子题材">
              <input
                className="ink-input"
                value={setting.sub_genre ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({ ...current, sub_genre: event.target.value }))
                }
              />
            </ProjectSettingField>
            <ProjectSettingField label="目标读者">
              <input
                className="ink-input"
                value={setting.target_readers ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({ ...current, target_readers: event.target.value }))
                }
              />
            </ProjectSettingField>
            <ProjectSettingField label="整体语气">
              <input
                className="ink-input"
                value={setting.tone ?? ""}
                onChange={(event) => setSetting((current) => ({ ...current, tone: event.target.value }))}
              />
            </ProjectSettingField>
          </div>
        </fieldset>

        <fieldset className="border border-[var(--line-soft)] rounded-[var(--radius-lg)] p-7 m-0 bg-gradient-to-br from-[var(--bg-surface)] to-[rgba(255,255,255,0.95)] transition-all relative">
          <legend className="text-[0.75rem] font-semibold text-[var(--text-secondary)] px-2 ml-2 tracking-[0.08em] uppercase">角色设定</legend>
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
            <ProjectSettingField label="主角姓名">
              <input
                className="ink-input"
                value={setting.protagonist?.name ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({
                    ...current,
                    protagonist: { ...current.protagonist, name: event.target.value },
                  }))
                }
              />
            </ProjectSettingField>
            <ProjectSettingField label="主角身份">
              <input
                className="ink-input"
                value={setting.protagonist?.identity ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({
                    ...current,
                    protagonist: { ...current.protagonist, identity: event.target.value },
                  }))
                }
              />
            </ProjectSettingField>
          </div>
        </fieldset>

        <fieldset className="border border-[var(--line-soft)] rounded-[var(--radius-lg)] p-7 m-0 bg-gradient-to-br from-[var(--bg-surface)] to-[rgba(255,255,255,0.95)] transition-all relative">
          <legend className="text-[0.75rem] font-semibold text-[var(--text-secondary)] px-2 ml-2 tracking-[0.08em] uppercase">世界观</legend>
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
            <ProjectSettingField label="世界名称">
              <input
                className="ink-input"
                value={setting.world_setting?.name ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({
                    ...current,
                    world_setting: { ...current.world_setting, name: event.target.value },
                  }))
                }
              />
            </ProjectSettingField>
            <ProjectSettingField label="力量体系">
              <input
                className="ink-input"
                value={setting.world_setting?.power_system ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({
                    ...current,
                    world_setting: { ...current.world_setting, power_system: event.target.value },
                  }))
                }
              />
            </ProjectSettingField>
          </div>
        </fieldset>

        <fieldset className="border border-[var(--line-soft)] rounded-[var(--radius-lg)] p-7 m-0 bg-gradient-to-br from-[var(--bg-surface)] to-[rgba(255,255,255,0.95)] transition-all relative">
          <legend className="text-[0.75rem] font-semibold text-[var(--text-secondary)] px-2 ml-2 tracking-[0.08em] uppercase">规模设定</legend>
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
            <ProjectSettingField label="目标字数">
              <input
                className="ink-input"
                inputMode="numeric"
                value={setting.scale?.target_words ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({
                    ...current,
                    scale: {
                      ...current.scale,
                      target_words: event.target.value ? Number(event.target.value) : undefined,
                    },
                  }))
                }
              />
            </ProjectSettingField>
            <ProjectSettingField label="目标章节">
              <input
                className="ink-input"
                inputMode="numeric"
                value={setting.scale?.target_chapters ?? ""}
                onChange={(event) =>
                  setSetting((current) => ({
                    ...current,
                    scale: {
                      ...current.scale,
                      target_chapters: event.target.value ? Number(event.target.value) : undefined,
                    },
                  }))
                }
              />
            </ProjectSettingField>
          </div>
        </fieldset>

        <div className="relative rounded-[var(--radius-md)] transition-all focus-within:shadow-[0_0_0_3px_rgba(90,122,107,0.12),0_2px_8px_rgba(90,122,107,0.08)] focus-within:bg-[rgba(255,255,255,0.02)]">
          <ProjectSettingField label="核心冲突">
            <textarea
              className="ink-textarea min-h-32"
              value={setting.core_conflict ?? ""}
              onChange={(event) =>
                setSetting((current) => ({ ...current, core_conflict: event.target.value }))
              }
            />
          </ProjectSettingField>
        </div>

        <div className="relative rounded-[var(--radius-md)] transition-all focus-within:shadow-[0_0_0_3px_rgba(90,122,107,0.12),0_2px_8px_rgba(90,122,107,0.08)] focus-within:bg-[rgba(255,255,255,0.02)]">
          <ProjectSettingField label="剧情走向">
            <textarea
              className="ink-textarea min-h-32"
              value={setting.plot_direction ?? ""}
              onChange={(event) =>
                setSetting((current) => ({ ...current, plot_direction: event.target.value }))
              }
            />
          </ProjectSettingField>
        </div>

        <div className="relative rounded-[var(--radius-md)] transition-all focus-within:shadow-[0_0_0_3px_rgba(90,122,107,0.12),0_2px_8px_rgba(90,122,107,0.08)] focus-within:bg-[rgba(255,255,255,0.02)]">
          <ProjectSettingField label="特殊要求">
            <textarea
              className="ink-textarea min-h-28"
              value={setting.special_requirements ?? ""}
              onChange={(event) =>
                setSetting((current) => ({ ...current, special_requirements: event.target.value }))
              }
            />
          </ProjectSettingField>
        </div>
        {lastImpact ? <ProjectSettingImpactPanel impact={lastImpact} /> : null}
      </div>
    </SectionCard>
  );
}
