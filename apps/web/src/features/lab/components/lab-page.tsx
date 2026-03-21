"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { createAnalysis, getAnalysis, listAnalyses } from "@/lib/api/analysis";
import { getErrorMessage } from "@/lib/api/client";
import type { AnalysisType } from "@/lib/api/types";

type LabPageProps = {
  projectId: string;
};

const ANALYSIS_TYPES: AnalysisType[] = ["plot", "character", "style", "pacing", "structure"];

export function LabPage({ projectId }: LabPageProps) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [formState, setFormState] = useState({
    analysisType: "plot" as AnalysisType,
    sourceTitle: "",
    result: '{\n  "summary": ""\n}',
    suggestions: '{\n  "next_step": ""\n}',
  });

  const listQuery = useQuery({
    queryKey: ["analyses", projectId],
    queryFn: () => listAnalyses(projectId),
  });

  const activeId = selectedId ?? listQuery.data?.[0]?.id ?? null;

  const detailQuery = useQuery({
    queryKey: ["analysis-detail", projectId, activeId],
    queryFn: () => getAnalysis(projectId, activeId as string),
    enabled: Boolean(activeId),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createAnalysis(projectId, {
        analysis_type: formState.analysisType,
        source_title: formState.sourceTitle || undefined,
        result: JSON.parse(formState.result),
        suggestions: JSON.parse(formState.suggestions),
      }),
    onSuccess: (result) => {
      setFeedback("分析记录已创建。");
      setSelectedId(result.id);
      queryClient.invalidateQueries({ queryKey: ["analyses", projectId] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const selectedSummary = useMemo(
    () => listQuery.data?.find((item) => item.id === activeId) ?? null,
    [activeId, listQuery.data],
  );

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_1fr_360px]">
      <aside className="panel-shell space-y-3 p-5">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent-ink)]">Lab</p>
          <h1 className="font-serif text-2xl font-semibold">分析结果工作台</h1>
        </div>
        {listQuery.data?.length ? (
          listQuery.data.map((item) => (
            <button
              key={item.id}
              className="ink-tab w-full justify-between"
              data-active={item.id === activeId}
              onClick={() => setSelectedId(item.id)}
            >
              <span>{item.source_title ?? item.analysis_type}</span>
              <StatusBadge status="active" label={item.analysis_type} />
            </button>
          ))
        ) : (
          <EmptyState
            title="暂无分析记录"
            description="右侧表单可以直接创建第一条分析结果。"
          />
        )}
      </aside>

      <SectionCard
        title={selectedSummary?.source_title ?? "分析详情"}
        description="Lab 当前只负责分析记录的创建、列表与详情查看。"
      >
        {detailQuery.isLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载分析详情...</p> : null}
        {detailQuery.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            {getErrorMessage(detailQuery.error)}
          </div>
        ) : null}
        {detailQuery.data ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <StatusBadge status="active" label={detailQuery.data.analysis_type} />
              {detailQuery.data.generated_skill_key ? (
                <StatusBadge status="approved" label={detailQuery.data.generated_skill_key} />
              ) : null}
            </div>
            <CodeBlock value={detailQuery.data.result} />
            {detailQuery.data.suggestions ? <CodeBlock value={detailQuery.data.suggestions} /> : null}
          </div>
        ) : null}
      </SectionCard>

      <form
        className="panel-shell space-y-4 p-5"
        onSubmit={(event) => {
          event.preventDefault();
          setFeedback(null);
          createMutation.mutate();
        }}
      >
        <div className="space-y-1">
          <h2 className="font-serif text-xl font-semibold">新建分析</h2>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            当前结果字段保持结构化 JSON，便于和后端 DTO 对齐。
          </p>
        </div>

        <label className="block space-y-2">
          <span className="label-text">分析类型</span>
          <select
            className="ink-select"
            value={formState.analysisType}
            onChange={(event) =>
              setFormState((current) => ({
                ...current,
                analysisType: event.target.value as AnalysisType,
              }))
            }
          >
            {ANALYSIS_TYPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-2">
          <span className="label-text">来源标题</span>
          <input
            className="ink-input"
            value={formState.sourceTitle}
            onChange={(event) =>
              setFormState((current) => ({ ...current, sourceTitle: event.target.value }))
            }
          />
        </label>

        <label className="block space-y-2">
          <span className="label-text">result JSON</span>
          <textarea
            className="ink-textarea min-h-40"
            value={formState.result}
            onChange={(event) => setFormState((current) => ({ ...current, result: event.target.value }))}
          />
        </label>

        <label className="block space-y-2">
          <span className="label-text">suggestions JSON</span>
          <textarea
            className="ink-textarea min-h-32"
            value={formState.suggestions}
            onChange={(event) =>
              setFormState((current) => ({ ...current, suggestions: event.target.value }))
            }
          />
        </label>

        {feedback ? (
          <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
            {feedback}
          </div>
        ) : null}

        <button className="ink-button w-full" disabled={createMutation.isPending} type="submit">
          {createMutation.isPending ? "创建中..." : "创建分析"}
        </button>
      </form>
    </div>
  );
}
