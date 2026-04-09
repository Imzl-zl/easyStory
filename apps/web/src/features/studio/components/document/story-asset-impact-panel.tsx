"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import { getStoryAssetLabel } from "@/features/studio/components/document/story-asset-editor-support";
import type { StoryAssetImpactSummary } from "@/lib/api/types";

type StoryAssetImpactPanelProps = {
  assetType: "outline" | "opening_plan";
  impact: StoryAssetImpactSummary;
};

const TARGET_LABELS = {
  opening_plan: "开篇设计",
  chapter: "已确认章节",
  chapter_tasks: "章节任务",
} as const;

export function StoryAssetImpactPanel({ assetType, impact }: StoryAssetImpactPanelProps) {
  const assetLabel = getStoryAssetLabel(assetType);

  return (
    <section className="panel-muted space-y-4 rounded-[28px] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-sm text-[var(--text-secondary)]">最近一次操作影响</p>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            {impact.has_impact
              ? `本次${assetLabel}更新已经同步到下游真值，以下内容已被标记为 stale。`
              : "本次操作没有触发新的 stale 传播，当前下游内容保持原状。"}
          </p>
        </div>
        <StatusBadge
          status={impact.has_impact ? "stale" : "ready"}
          label={impact.has_impact ? `${impact.total_affected_entries} 项受影响` : "无下游影响"}
        />
      </div>

      {impact.has_impact ? (
        <div className="space-y-3">
          {impact.items.map((item) => (
            <article key={item.target} className="rounded-2xl bg-[rgba(22,28,45,0.05)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {TARGET_LABELS[item.target]}
                </p>
                <StatusBadge status="stale" label={`${item.count} 项`} />
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{item.message}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
