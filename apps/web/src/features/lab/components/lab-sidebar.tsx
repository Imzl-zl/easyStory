"use client";

import { AppSelect } from "@/components/ui/app-select";
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
        <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent-ink)]">洞察书架</p>
        <h1 className="font-serif text-2xl font-semibold">项目洞察列表</h1>
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
        <span className="label-text">分析类型</span>
        <AppSelect
          disabled={isPending}
          options={[
            { label: "全部类型", value: LAB_ANALYSIS_FILTER_ALL },
            ...LAB_ANALYSIS_TYPES.map((item) => ({ label: item, value: item })),
          ]}
          value={filters.analysisType}
          onChange={(value) => onFilterChange({ analysisType: value as LabAnalysisFilterState["analysisType"] })}
        />
      </label>
      <label className="block space-y-2">
        <span className="label-text">关联正文片段</span>
        <input
          className="ink-input"
          disabled={isPending}
          placeholder="可选，输入某段正文的内容 ID"
          value={filters.contentId}
          onChange={(event) => onFilterChange({ contentId: event.target.value })}
        />
      </label>
      <label className="block space-y-2">
        <span className="label-text">来源 Skill</span>
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
          ? "尝试调整过滤条件。"
          : "创建你的第一条分析记录。"
      }
    />
  );
}
