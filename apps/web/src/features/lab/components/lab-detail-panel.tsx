"use client";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import type { AnalysisDetail } from "@/lib/api/types";

import { formatLabAnalysisTime, formatLabAnalysisTitle } from "./lab-support";

type LabDetailPanelProps = {
  activeId: string | null;
  analysis: AnalysisDetail | undefined;
  errorMessage: string | null;
  hasActiveFilters: boolean;
  isDeletePending: boolean;
  isLoading: boolean;
  onRequestDelete: (analysis: AnalysisDetail) => void;
};

export function LabDetailPanel({
  activeId,
  analysis,
  errorMessage,
  hasActiveFilters,
  isDeletePending,
  isLoading,
  onRequestDelete,
}: Readonly<LabDetailPanelProps>) {
  return (
    <SectionCard
      title={analysis ? formatLabAnalysisTitle(analysis) : "分析详情"}
      description="详情区只负责查看当前分析结果与元数据，不在这里继续扩展成编辑工作台。"
      action={
        analysis ? (
          <button
            className="ink-button-danger"
            disabled={isDeletePending}
            onClick={() => onRequestDelete(analysis)}
            type="button"
          >
            {isDeletePending ? "删除中..." : "删除分析"}
          </button>
        ) : null
      }
    >
      <LabDetailContent
        activeId={activeId}
        analysis={analysis}
        errorMessage={errorMessage}
        hasActiveFilters={hasActiveFilters}
        isLoading={isLoading}
      />
    </SectionCard>
  );
}

function LabDetailContent({
  activeId,
  analysis,
  errorMessage,
  hasActiveFilters,
  isLoading,
}: Readonly<{
  activeId: string | null;
  analysis: AnalysisDetail | undefined;
  errorMessage: string | null;
  hasActiveFilters: boolean;
  isLoading: boolean;
}>) {
  if (!activeId) {
    return (
      <EmptyState
        title={hasActiveFilters ? "当前过滤条件下没有分析记录" : "先选一条分析记录"}
        description={hasActiveFilters ? "调整过滤器后，再查看分析详情。" : "左侧选中一条分析记录后，这里会展示详情。"}
      />
    );
  }
  if (isLoading && !analysis) {
    return <p className="text-sm text-[var(--text-secondary)]">正在加载分析详情...</p>;
  }
  if (errorMessage && !analysis) {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {errorMessage}
      </div>
    );
  }
  if (!analysis) {
    return <EmptyState title="暂无分析详情" description="当前选中项没有可展示的数据。" />;
  }
  return (
    <div className="space-y-4">
      {errorMessage ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {errorMessage}
        </div>
      ) : null}
      <LabAnalysisMeta analysis={analysis} />
      {analysis.analysis_scope ? <CodeBlock value={analysis.analysis_scope} /> : null}
      <CodeBlock value={analysis.result} />
      {analysis.suggestions ? <CodeBlock value={analysis.suggestions} /> : null}
    </div>
  );
}

function LabAnalysisMeta({ analysis }: Readonly<{ analysis: AnalysisDetail }>) {
  return (
    <div className="space-y-3 rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.56)] p-4">
      <div className="flex flex-wrap gap-2">
        <StatusBadge status="active" label={analysis.analysis_type} />
        {analysis.generated_skill_key ? <StatusBadge status="approved" label={analysis.generated_skill_key} /> : null}
      </div>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">来源标题：{analysis.source_title ?? "未命名来源"}</p>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">content_id：{analysis.content_id ?? "未绑定内容"}</p>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">创建时间：{formatLabAnalysisTime(analysis.created_at)}</p>
    </div>
  );
}
