"use client";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import type { AnalysisDetail } from "@/lib/api/types";

import { formatLabAnalysisTime, formatLabAnalysisTitle } from "./lab-support";

type LabDetailPanelProps = {
  activeId: string | null;
  analysis: AnalysisDetail | undefined;
  errorMessage: string | null;
  hasActiveFilters: boolean;
  isDeletePending: boolean;
  isLoading: boolean;
  onRequestDelete: (analysisId: string) => void;
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
    <div className="h-full flex flex-col rounded" style={{ background: "#1a1d23", border: "1px solid #2a2f35" }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid #2a2f35" }}>
        <span className="text-[12px] font-medium" style={{ color: "#9ca3af" }}>
          {analysis ? formatLabAnalysisTitle(analysis) : "洞察详情"}
        </span>
        {analysis ? (
          <button
            className="px-3 py-1.5 rounded text-[11px] font-medium transition-all disabled:opacity-40"
            style={{ background: "rgba(220, 38, 38, 0.1)", color: "#f87171", border: "1px solid rgba(220, 38, 38, 0.2)" }}
            disabled={isDeletePending}
            onClick={() => onRequestDelete(analysis.id)}
            type="button"
          >
            {isDeletePending ? "删除中..." : "删除"}
          </button>
        ) : null}
      </div>
      <div className="flex-1 overflow-auto p-4">
        <LabDetailContent
          activeId={activeId}
          analysis={analysis}
          errorMessage={errorMessage}
          hasActiveFilters={hasActiveFilters}
          isLoading={isLoading}
        />
      </div>
    </div>
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
        description={hasActiveFilters ? "尝试调整过滤条件。" : "选择左侧记录查看详情。"}
      />
    );
  }
  if (isLoading && !analysis) {
    return <p className="text-[11px]" style={{ color: "#6b7280" }}>正在加载洞察详情...</p>;
  }
  if (errorMessage && !analysis) {
    return (
      <div className="rounded px-3 py-2 text-[11px]" style={{ background: "rgba(220, 38, 38, 0.08)", color: "#f87171" }}>
        {errorMessage}
      </div>
    );
  }
  if (!analysis) {
    return <EmptyState title="暂无洞察详情" description="该记录暂无可展示的数据。" />;
  }
  return (
    <div className="space-y-3">
      {errorMessage ? (
        <div className="rounded px-3 py-2 text-[11px]" style={{ background: "rgba(220, 38, 38, 0.08)", color: "#f87171" }}>
          {errorMessage}
        </div>
      ) : null}
      <LabAnalysisMeta analysis={analysis} />
      {analysis.analysis_scope ? (
        <div className="rounded p-4" style={{ background: "#111418", border: "1px solid #1f2328" }}>
          <h3 className="text-[12px] font-medium mb-2" style={{ color: "#6b7280" }}>分析范围</h3>
          <CodeBlock value={analysis.analysis_scope} />
        </div>
      ) : null}
      <div className="rounded p-4" style={{ background: "#111418", border: "1px solid #1f2328" }}>
        <h3 className="text-[12px] font-medium mb-2" style={{ color: "#6b7280" }}>分析结果</h3>
        <CodeBlock value={analysis.result} />
      </div>
      {analysis.suggestions ? (
        <div className="rounded p-4" style={{ background: "#111418", border: "1px solid #1f2328" }}>
          <h3 className="text-[12px] font-medium mb-2" style={{ color: "#6b7280" }}>后续建议</h3>
          <CodeBlock value={analysis.suggestions} />
        </div>
      ) : null}
    </div>
  );
}

function LabAnalysisMeta({ analysis }: Readonly<{ analysis: AnalysisDetail }>) {
  return (
    <div className="rounded p-3" style={{ background: "#111418", border: "1px solid #1f2328" }}>
      <div className="grid gap-2 grid-cols-2">
        <MetaItem label="分析类型" value={analysis.analysis_type} />
        <MetaItem label="来源标题" value={analysis.source_title ?? "未命名来源"} />
        <MetaItem label="关联正文" value={analysis.content_id ?? "未绑定内容"} />
        <MetaItem label="创建时间" value={formatLabAnalysisTime(analysis.created_at)} />
        {analysis.generated_skill_key ? (
          <MetaItem label="来源 Skill" value={analysis.generated_skill_key} />
        ) : null}
      </div>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] mb-0.5" style={{ color: "#4b5563" }}>{label}</p>
      <p className="text-[12px] font-medium" style={{ color: "#9ca3af" }}>{value}</p>
    </div>
  );
}
