"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import type { AnalysisSummary } from "@/lib/api/types";

import {
  LAB_ANALYSIS_FILTER_ALL,
  LAB_ANALYSIS_TYPES,
  formatLabAnalysisTime,
  formatLabAnalysisTitle,
  hasActiveLabAnalysisFilters,
  type LabAnalysisFilterState,
} from "./lab-support";

type LabSidebarProps = {
  activeId: string | null;
  analyses: AnalysisSummary[];
  errorMessage: string | null;
  filters: LabAnalysisFilterState;
  isLoading: boolean;
  isPending: boolean;
  onFilterChange: (patch: Partial<LabAnalysisFilterState>) => void;
  onSelect: (analysisId: string) => void;
};

export function LabSidebar({
  activeId,
  analyses,
  errorMessage,
  filters,
  isLoading,
  isPending,
  onFilterChange,
  onSelect,
}: Readonly<LabSidebarProps>) {
  const showEmptyState = analyses.length === 0 && !isLoading && !errorMessage;

  return (
    <aside className="panel-shell space-y-4 p-5">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent-ink)]">Lab</p>
        <h1 className="font-serif text-2xl font-semibold">分析结果工作台</h1>
      </div>
      <LabFilters filters={filters} isPending={isPending} onFilterChange={onFilterChange} />
      {isLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载分析列表...</p> : null}
      {errorMessage ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {errorMessage}
        </div>
      ) : null}
      <LabAnalysisList
        activeId={activeId}
        analyses={analyses}
        filters={filters}
        isPending={isPending}
        showEmptyState={showEmptyState}
        onSelect={onSelect}
      />
    </aside>
  );
}

function LabFilters({
  filters,
  isPending,
  onFilterChange,
}: Readonly<{
  filters: LabAnalysisFilterState;
  isPending: boolean;
  onFilterChange: (patch: Partial<LabAnalysisFilterState>) => void;
}>) {
  return (
    <div className="space-y-3 rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.56)] p-4">
      <label className="block space-y-2">
        <span className="label-text">analysis_type</span>
        <select
          className="ink-select"
          disabled={isPending}
          value={filters.analysisType}
          onChange={(event) => onFilterChange({ analysisType: event.target.value as LabAnalysisFilterState["analysisType"] })}
        >
          <option value={LAB_ANALYSIS_FILTER_ALL}>全部类型</option>
          {LAB_ANALYSIS_TYPES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="block space-y-2">
        <span className="label-text">content_id</span>
        <input
          className="ink-input"
          disabled={isPending}
          placeholder="可选，粘贴某条内容 ID"
          value={filters.contentId}
          onChange={(event) => onFilterChange({ contentId: event.target.value })}
        />
      </label>
      <label className="block space-y-2">
        <span className="label-text">generated_skill_key</span>
        <input
          className="ink-input"
          disabled={isPending}
          placeholder="可选，例如 skill.style.river"
          value={filters.generatedSkillKey}
          onChange={(event) => onFilterChange({ generatedSkillKey: event.target.value })}
        />
      </label>
    </div>
  );
}

function LabAnalysisList({
  activeId,
  analyses,
  filters,
  isPending,
  onSelect,
  showEmptyState,
}: Readonly<{
  activeId: string | null;
  analyses: AnalysisSummary[];
  filters: LabAnalysisFilterState;
  isPending: boolean;
  onSelect: (analysisId: string) => void;
  showEmptyState: boolean;
}>) {
  if (analyses.length > 0) {
    return (
      <div className="space-y-3">
        {analyses.map((analysis) => (
          <button
            key={analysis.id}
            className="ink-tab w-full flex-col items-start gap-2"
            data-active={analysis.id === activeId}
            disabled={isPending}
            onClick={() => onSelect(analysis.id)}
            type="button"
          >
            <span className="text-left font-medium text-[var(--text-primary)]">{formatLabAnalysisTitle(analysis)}</span>
            <div className="flex w-full flex-wrap items-center gap-2 text-xs text-[var(--text-secondary)]">
              <StatusBadge status="active" label={analysis.analysis_type} />
              {analysis.generated_skill_key ? (
                <StatusBadge status="approved" label={analysis.generated_skill_key} />
              ) : null}
              <span>{formatLabAnalysisTime(analysis.created_at)}</span>
            </div>
          </button>
        ))}
      </div>
    );
  }
  if (!showEmptyState) {
    return null;
  }
  return (
    <EmptyState
      title={hasActiveLabAnalysisFilters(filters) ? "没有匹配的分析记录" : "暂无分析记录"}
      description={
        hasActiveLabAnalysisFilters(filters)
          ? "当前过滤条件下没有分析记录，可调整 analysis_type / content_id / generated_skill_key。"
          : "右侧表单可以直接创建第一条分析结果。"
      }
    />
  );
}
