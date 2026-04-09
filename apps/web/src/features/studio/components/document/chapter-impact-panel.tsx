"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import type { ChapterImpactSummary } from "@/lib/api/types";

type ChapterImpactPanelProps = {
  impact: ChapterImpactSummary;
};

const TARGET_LABELS = {
  chapter: "后续已确认章节",
} as const;

export function ChapterImpactPanel({ impact }: ChapterImpactPanelProps) {
  return (
    <section className="panel-muted space-y-4 rounded-[28px] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-sm text-[var(--text-secondary)]">最近一次章节变更影响</p>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            {impact.has_impact
              ? "本次章节变更已经同步标记下游正文，以下章节需要按范围复核。"
              : "本次章节变更没有触发新的 stale 传播，当前下游正文保持原状。"}
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
