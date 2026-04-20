"use client";

import { useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildProjectSettingSections,
} from "@/features/project/components/project-setting-summary-support";
import { ProjectSettingSummaryEditor } from "@/features/project-settings/components/project-setting-summary-editor";
import type {
  ProjectSetting,
  ProjectSettingImpactSummary,
  ProjectSettingSnapshot,
} from "@/lib/api/types";

type ProjectSettingSummaryPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
  projectSetting: ProjectSetting | null;
  projectId: string;
};

export function ProjectSettingSummaryPanel({
  onDirtyChange,
  projectSetting,
  projectId,
}: Readonly<ProjectSettingSummaryPanelProps>) {
  const [isEditing, setIsEditing] = useState(false);
  const [lastImpact, setLastImpact] = useState<ProjectSettingImpactSummary | null>(null);
  const sections = projectSetting ? buildProjectSettingSections(projectSetting) : [];
  const hasSummary = sections.length > 0;
  const summaryText = hasSummary
    ? "这份项目摘要只负责快速浏览题材、冲突、人物入口和规模。长期设定仍以项目文稿为准。"
    : "还没有结构化摘要。先把项目说明和设定文稿写清楚，再按需提炼一版项目摘要。";

  return (
    <div className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.85fr)]">
        <section className="panel-muted min-w-0 space-y-4 rounded-3xl p-5">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-accent-primary">
              结构化摘要
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="font-serif text-xl font-semibold text-text-primary">
                快速看主要信息
              </h2>
              <StatusBadge status={hasSummary ? "ready" : "draft"} />
              <button
                className="ink-button-secondary h-9 px-4"
                type="button"
                onClick={() => setIsEditing(true)}
              >
                更新摘要
              </button>
            </div>
            <p className="text-sm leading-6 text-text-secondary">{summaryText}</p>
          </div>
        </section>

        <section className="rounded-3xl bg-surface shadow-sm p-5">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.18em] text-text-secondary">
              用法说明
            </p>
            <div className="space-y-3 text-sm leading-6 text-text-secondary">
              <p>这里主要用来总览题材、冲突、人物入口和篇幅计划，不要求把完整设定压进固定表单。</p>
              <p>详细世界观、人物小传、伏笔和长期约束，更适合继续放在项目文档里维护。</p>
              <p>这份摘要会继续参与大纲、开篇和章节生成；如果保存了新的摘要，下游已确认内容会按影响标记为 stale，方便重新核对。</p>
            </div>
          </div>
        </section>
      </div>

      {isEditing ? (
        <ProjectSettingSummaryEditor
          key={`${projectId}:${JSON.stringify(projectSetting ?? {})}`}
          initialSetting={projectSetting}
          projectId={projectId}
          onCancel={() => {
            onDirtyChange?.(false);
            setIsEditing(false);
          }}
          onDirtyChange={onDirtyChange}
          onSaved={(snapshot) => {
            handleSummarySaved({
              onDirtyChange,
              setIsEditing,
              setLastImpact,
              snapshot,
            });
          }}
        />
      ) : null}

      {lastImpact ? <ProjectSettingImpactCallout impact={lastImpact} /> : null}

      {hasSummary ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {sections.map((section) => (
            <section
              key={section.title}
              className="min-w-0 rounded-2xl bg-surface shadow-sm p-5"
            >
              <div className="space-y-3">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.18em] text-text-secondary">
                    项目摘要
                  </p>
                  <h3 className="font-serif text-lg font-semibold text-text-primary">
                    {section.title}
                  </h3>
                </div>
                <dl className="space-y-3">
                  {section.items.map((item) => (
                    <div
                      key={`${section.title}-${item.label}`}
                      className="grid min-w-0 gap-2 border-b border-line-soft pb-3 last:border-b-0 last:pb-0 md:grid-cols-[96px_minmax(0,1fr)]"
                    >
                      <dt className="text-sm font-medium text-text-secondary">
                        {item.label}
                      </dt>
                      <dd className="min-w-0 break-words text-sm leading-6 text-text-primary">
                        {item.value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </section>
          ))}
        </div>
      ) : (
        <EmptyState
          description="可以继续用 AI 或文档补充。"
          title="还没有项目摘要"
        />
      )}
    </div>
  );
}

function ProjectSettingImpactCallout({
  impact,
}: Readonly<{ impact: ProjectSettingImpactSummary }>) {
  return (
    <section className="callout-warning p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-text-primary">最近一次保存影响</p>
          <p className="text-sm leading-6 text-text-secondary">
            {impact.has_impact
              ? "本次摘要更新已经同步到下游真值，相关内容已标记为 stale。"
              : "本次摘要保存没有触发新的下游 stale。"}
          </p>
        </div>
        <StatusBadge
          status={impact.has_impact ? "stale" : "ready"}
          label={impact.has_impact ? `${impact.total_affected_entries} 项受影响` : "无下游影响"}
        />
      </div>
      {impact.items.length > 0 ? (
        <div className="mt-3 space-y-2">
          {impact.items.map((item) => (
            <div
              key={item.target}
              className="rounded-2xl border border-accent-warning/14 bg-glass px-4 py-3 text-sm leading-6 text-text-secondary"
            >
              <span className="font-medium text-text-primary">{formatImpactTarget(item.target)}</span>
              ：{item.message}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function handleSummarySaved(options: {
  onDirtyChange?: (isDirty: boolean) => void;
  setIsEditing: (isEditing: boolean) => void;
  setLastImpact: (impact: ProjectSettingImpactSummary | null) => void;
  snapshot: ProjectSettingSnapshot;
}) {
  options.setLastImpact(options.snapshot.impact);
  options.setIsEditing(false);
  options.onDirtyChange?.(false);
}

function formatImpactTarget(target: ProjectSettingImpactSummary["items"][number]["target"]) {
  if (target === "outline") return "大纲";
  if (target === "opening_plan") return "开篇设计";
  if (target === "chapter") return "已确认章节";
  return "章节任务";
}
