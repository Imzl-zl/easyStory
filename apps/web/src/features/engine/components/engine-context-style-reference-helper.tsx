"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AppSelect } from "@/components/ui/app-select";
import { showAppNotice } from "@/components/ui/app-notice";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { listAnalyses } from "@/lib/api/analysis";
import { getErrorMessage } from "@/lib/api/client";
import type { AnalysisSummary } from "@/lib/api/types";

import { formatAnalysisOptionLabel } from "./engine-context-format";
import {
  parseInjectFields,
  upsertStyleReferenceExtraInject,
} from "./engine-context-request-support";

const EMPTY_ANALYSES: AnalysisSummary[] = [];

type EngineContextStyleReferenceHelperProps = {
  extraInjectText: string;
  projectId: string;
  onApply: (nextValue: string) => void;
};

export function EngineContextStyleReferenceHelper({
  extraInjectText,
  projectId,
  onApply,
}: EngineContextStyleReferenceHelperProps) {
  const [generatedSkillKey, setGeneratedSkillKey] = useState("");
  const [selectedAnalysisId, setSelectedAnalysisId] = useState("");
  const [injectFieldsInput, setInjectFieldsInput] = useState("writing_style");
  const deferredGeneratedSkillKey = useDeferredValue(generatedSkillKey.trim());

  const analysesQuery = useQuery({
    queryKey: ["engine-context-style-analyses", projectId, deferredGeneratedSkillKey],
    queryFn: () =>
      listAnalyses(projectId, {
        analysisType: "style",
        generatedSkillKey: deferredGeneratedSkillKey || undefined,
      }),
  });

  const analyses = analysesQuery.data ?? EMPTY_ANALYSES;
  const selectedAnalysis = useMemo(
    () => analyses.find((item) => item.id === selectedAnalysisId) ?? null,
    [analyses, selectedAnalysisId],
  );

  useEffect(() => {
    if (analyses.length === 0) {
      setSelectedAnalysisId("");
      return;
    }
    if (!selectedAnalysisId || !analyses.some((item) => item.id === selectedAnalysisId)) {
      setSelectedAnalysisId(analyses[0].id);
    }
  }, [analyses, selectedAnalysisId]);

  const applyStyleReference = () => {
    try {
      if (!selectedAnalysisId) {
        throw new Error("请先选择一条 style analysis。");
      }
      const nextValue = upsertStyleReferenceExtraInject(extraInjectText, {
        analysisId: selectedAnalysisId,
        injectFields: parseInjectFields(injectFieldsInput),
      });
      onApply(nextValue);
      showAppNotice({
        content: "已写入 style_reference。",
        title: "风格参考助手",
        tone: "success",
      });
    } catch (error) {
      showAppNotice({
        content: getErrorMessage(error),
        title: "风格参考助手",
        tone: "danger",
      });
    }
  };

  return (
    <section className="rounded-2xl bg-muted shadow-sm p-4">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">风格参考助手</h3>
        <p className="text-sm leading-6 text-text-secondary">
          按最新优先列出 style 分析，选中后自动写入 `style_reference`，不再手填
          `analysis_id`。
        </p>
      </header>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="block space-y-2">
          <span className="label-text">generated_skill_key 过滤</span>
          <input
            className="ink-input"
            placeholder="可选，例如 skill.style.river"
            value={generatedSkillKey}
            onChange={(event) => setGeneratedSkillKey(event.target.value)}
          />
        </label>
        <label className="block space-y-2">
          <span className="label-text">inject_fields</span>
          <input
            className="ink-input"
            placeholder="writing_style, narrative_perspective"
            value={injectFieldsInput}
            onChange={(event) => setInjectFieldsInput(event.target.value)}
          />
        </label>
      </div>

      <div className="mt-4 space-y-3">
        {analysesQuery.isLoading ? (
          <p className="text-sm text-text-secondary">正在加载 style 分析列表…</p>
        ) : null}
        {analysesQuery.error ? (
          <FeedbackMessage message={getErrorMessage(analysesQuery.error)} />
        ) : null}
        {!analysesQuery.isLoading && !analysesQuery.error && analyses.length === 0 ? (
          <EmptyState
            title="暂无可选 style 分析"
            description="暂无 style 分析记录，可前往 Lab 创建。"
          />
        ) : null}
        {analyses.length > 0 ? (
          <>
            <label className="block space-y-2">
              <span className="label-text">风格分析记录</span>
              <AppSelect
                options={analyses.map((analysis) => ({
                  label: formatAnalysisOptionLabel(analysis),
                  value: analysis.id,
                }))}
                value={selectedAnalysisId}
                onChange={setSelectedAnalysisId}
              />
            </label>

            {selectedAnalysis ? <SelectedAnalysisCard analysis={selectedAnalysis} /> : null}

            <button className="ink-button-secondary" onClick={applyStyleReference}>
              写入 style_reference
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}

function SelectedAnalysisCard({ analysis }: Readonly<{ analysis: AnalysisSummary }>) {
  return (
    <div className="rounded-2xl bg-muted shadow-sm p-3">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status="active" label="style" />
        {analysis.generated_skill_key ? (
          <StatusBadge status="approved" label={analysis.generated_skill_key} />
        ) : null}
      </div>
      <p className="mt-3 text-sm font-medium text-text-primary">
        {analysis.source_title ?? "未命名来源"}
      </p>
      <p className="mt-1 text-sm leading-6 text-text-secondary">
        analysis_id: {analysis.id}
      </p>
    </div>
  );
}

function FeedbackMessage({
  message,
}: Readonly<{
  message: string;
}>) {
  return (
    <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
      {message}
    </div>
  );
}
