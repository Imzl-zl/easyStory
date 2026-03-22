"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { SectionCard } from "@/components/ui/section-card";
import { ProjectSettingImpactPanel } from "@/features/studio/components/project-setting-impact-panel";
import {
  buildSettingIssueSummary,
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
  projectId: string;
  initialSetting: ProjectSetting | null;
  completeness?: SettingCompletenessResult;
};

export function ProjectSettingEditor({
  projectId,
  initialSetting,
  completeness,
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
}: {
  projectId: string;
  initialSetting: ProjectSetting;
  completeness?: SettingCompletenessResult;
  lastImpact: ProjectSettingImpactSummary | null;
  onImpactChange: (impact: ProjectSettingImpactSummary | null) => void;
}) {
  const queryClient = useQueryClient();
  const [setting, setSetting] = useState<ProjectSetting>(initialSetting);
  const [feedback, setFeedback] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () => updateProjectSetting(projectId, setting),
    onSuccess: (result) => {
      onImpactChange(result.impact);
      setFeedback(buildSettingSaveFeedback(result.impact));
      invalidateProjectSettingQueries(queryClient, projectId, result.impact);
    },
    onError: (error) => {
      onImpactChange(null);
      setFeedback(getErrorMessage(error));
    },
  });

  const checkMutation = useMutation({
    mutationFn: () => checkProjectSetting(projectId),
    onSuccess: (result) => {
      setFeedback(`完整度检查完成：${result.status}`);
      queryClient.setQueryData(["setting-check", projectId], result);
      queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const issueSummary = buildSettingIssueSummary(completeness);

  return (
    <SectionCard
      title="Project Setting"
      description="项目设定是当前创作主链路的真值源。保存后可再次执行完整度检查。"
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
      <div className="space-y-5">
        <div className="panel-muted flex flex-wrap items-start justify-between gap-3 p-4">
          <div className="space-y-2">
            <p className="text-sm text-[var(--text-secondary)]">设定完整度</p>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">{issueSummary}</p>
          </div>
          <StatusBadge status={completeness?.status ?? "draft"} label={completeness?.status ?? "未检查"} />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Field label="题材">
            <input
              className="ink-input"
              value={setting.genre ?? ""}
              onChange={(event) => setSetting((current) => ({ ...current, genre: event.target.value }))}
            />
          </Field>
          <Field label="子题材">
            <input
              className="ink-input"
              value={setting.sub_genre ?? ""}
              onChange={(event) =>
                setSetting((current) => ({ ...current, sub_genre: event.target.value }))
              }
            />
          </Field>
          <Field label="目标读者">
            <input
              className="ink-input"
              value={setting.target_readers ?? ""}
              onChange={(event) =>
                setSetting((current) => ({ ...current, target_readers: event.target.value }))
              }
            />
          </Field>
          <Field label="整体语气">
            <input
              className="ink-input"
              value={setting.tone ?? ""}
              onChange={(event) => setSetting((current) => ({ ...current, tone: event.target.value }))}
            />
          </Field>
          <Field label="主角姓名">
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
          </Field>
          <Field label="主角身份">
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
          </Field>
          <Field label="世界名称">
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
          </Field>
          <Field label="力量体系">
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
          </Field>
          <Field label="目标字数">
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
          </Field>
          <Field label="目标章节">
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
          </Field>
        </div>

        <Field label="核心冲突">
          <textarea
            className="ink-textarea min-h-28"
            value={setting.core_conflict ?? ""}
            onChange={(event) =>
              setSetting((current) => ({ ...current, core_conflict: event.target.value }))
            }
          />
        </Field>

        <Field label="剧情走向">
          <textarea
            className="ink-textarea min-h-28"
            value={setting.plot_direction ?? ""}
            onChange={(event) =>
              setSetting((current) => ({ ...current, plot_direction: event.target.value }))
            }
          />
        </Field>

        <Field label="特殊要求">
          <textarea
            className="ink-textarea min-h-24"
            value={setting.special_requirements ?? ""}
            onChange={(event) =>
              setSetting((current) => ({ ...current, special_requirements: event.target.value }))
            }
          />
        </Field>

        {feedback ? (
          <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
            {feedback}
          </div>
        ) : null}

        {lastImpact ? <ProjectSettingImpactPanel impact={lastImpact} /> : null}
      </div>
    </SectionCard>
  );
}

function Field({
  label,
  children,
}: Readonly<{
  label: string;
  children: React.ReactNode;
}>) {
  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      {children}
    </label>
  );
}
