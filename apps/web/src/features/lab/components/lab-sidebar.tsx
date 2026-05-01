"use client";

import { AppSelect } from "@/components/ui/app-select";
import { EmptyState } from "@/components/ui/empty-state";
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
    <aside className="h-full flex flex-col space-y-3">
      {/* Filters */}
      <div className="rounded p-3" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
        <div className="space-y-2.5">
          <label className="block space-y-1">
            <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>分析类型</span>
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
          <label className="block space-y-1">
            <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>关联正文片段</span>
            <input
              className="w-full px-3 py-2 rounded text-[12px] outline-none"
              disabled={isPending}
              placeholder="可选，输入内容 ID"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
              value={filters.contentId}
              onChange={(event) => onFilterChange({ contentId: event.target.value })}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>来源 Skill</span>
            <input
              className="w-full px-3 py-2 rounded text-[12px] outline-none"
              disabled={isPending}
              placeholder="可选，例如 skill.style.river"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
              value={filters.generatedSkillKey}
              onChange={(event) => onFilterChange({ generatedSkillKey: event.target.value })}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
            />
          </label>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-auto min-h-0">
        {isLoading ? (
          <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>正在加载分析列表...</p>
        ) : null}
        {errorMessage ? (
          <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {errorMessage}
          </div>
        ) : null}
        <LabAnalysisList
          activeId={activeId}
          analyses={analyses}
          isPending={isPending}
          showEmptyState={showEmptyState}
          filters={filters}
          onSelect={onSelect}
        />
      </div>
    </aside>
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
      <div className="space-y-2">
        {analyses.map((analysis) => (
          <button
            key={analysis.id}
            className="w-full rounded p-3 text-left transition-all disabled:opacity-40"
            style={{
              background: analysis.id === activeId ? "var(--line-soft)" : "var(--bg-canvas)",
              border: `1px solid ${analysis.id === activeId ? "var(--bg-muted)" : "var(--line-soft)"}`,
            }}
            disabled={isPending}
            onClick={() => onSelect(analysis.id)}
            type="button"
          >
            <div className="flex items-center gap-1.5 mb-1.5">
              <StatusPill tone="active" label={analysis.analysis_type} />
              {analysis.generated_skill_key ? (
                <StatusPill tone="outline" label={analysis.generated_skill_key} />
              ) : null}
            </div>
            <p className="text-[12px] font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {formatLabAnalysisTitle(analysis)}
            </p>
            <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>
              {formatLabAnalysisTime(analysis.created_at)}
            </p>
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

function StatusPill({ tone, label }: { tone: string; label: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "var(--accent-success-soft)", text: "var(--accent-success)" },
    failed: { bg: "var(--accent-danger-soft)", text: "var(--accent-danger)" },
    warning: { bg: "var(--accent-warning-soft)", text: "var(--accent-warning)" },
    active: { bg: "var(--accent-primary-soft)", text: "var(--accent-primary)" },
    outline: { bg: "var(--line-soft)", text: "var(--text-secondary)" },
    draft: { bg: "var(--line-soft)", text: "var(--text-tertiary)" },
  };
  const c = colors[tone] || colors.outline;
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-medium"
      style={{ background: c.bg, color: c.text }}
    >
      {label}
    </span>
  );
}
