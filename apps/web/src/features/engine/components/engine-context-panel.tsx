"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { previewWorkflowContext } from "@/lib/api/context";
import { getErrorMessage } from "@/lib/api/client";
import type { ContextPreview, ContextPreviewSection } from "@/lib/api/types";

import {
  buildSectionDetail,
  formatCount,
  formatSectionLabel,
  formatSectionStatusLabel,
  formatTokenCount,
  resolveSectionTone,
} from "./engine-context-format";
import {
  EXTRA_INJECT_PLACEHOLDER,
  normalizeNodeId,
  parseChapterNumber,
  parseExtraInject,
} from "./engine-context-request-support";
import { EngineContextStyleReferenceHelper } from "./engine-context-style-reference-helper";

type EngineContextPanelProps = {
  projectId: string;
  workflowId: string;
  isWorkflowReady: boolean;
};

export function EngineContextPanel({
  projectId,
  workflowId,
  isWorkflowReady,
}: EngineContextPanelProps) {
  const [nodeId, setNodeId] = useState("");
  const [chapterNumber, setChapterNumber] = useState("");
  const [extraInjectText, setExtraInjectText] = useState("");

  const previewMutation = useMutation({
    mutationFn: () =>
      previewWorkflowContext(workflowId, {
        node_id: normalizeNodeId(nodeId),
        chapter_number: parseChapterNumber(chapterNumber),
        extra_inject: parseExtraInject(extraInjectText),
      }),
  });

  if (!isWorkflowReady) {
    return (
      <EmptyState
        title="尚未载入工作流"
        description="启动工作流后查看。"
      />
    );
  }

  return (
    <div className="space-y-4">
      <section className="panel-muted space-y-4 p-4">
        <header className="space-y-1">
          <h3 className="font-serif text-lg font-semibold">预览请求</h3>
          <p className="text-sm leading-6 text-text-secondary">
            试运行节点上下文。
          </p>
        </header>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="label-text">node_id</span>
            <input
              className="ink-input"
              value={nodeId}
              onChange={(event) => setNodeId(event.target.value)}
            />
          </label>
          <label className="block space-y-2">
            <span className="label-text">chapter_number</span>
            <input
              className="ink-input"
              inputMode="numeric"
              value={chapterNumber}
              onChange={(event) => setChapterNumber(event.target.value)}
            />
          </label>
        </div>

        <label className="block space-y-2">
          <span className="label-text">extra_inject JSON（可选）</span>
          <textarea
            className="ink-textarea min-h-40"
            placeholder={EXTRA_INJECT_PLACEHOLDER}
            value={extraInjectText}
            onChange={(event) => setExtraInjectText(event.target.value)}
          />
        </label>

        <EngineContextStyleReferenceHelper
          extraInjectText={extraInjectText}
          projectId={projectId}
          onApply={setExtraInjectText}
        />

        <button
          className="ink-button"
          disabled={previewMutation.isPending || !nodeId.trim()}
          onClick={() => previewMutation.mutate()}
        >
          {previewMutation.isPending ? "预览中..." : "预览上下文"}
        </button>

        {previewMutation.error ? (
          <FeedbackMessage tone="danger" message={getErrorMessage(previewMutation.error)} />
        ) : null}
      </section>

      {previewMutation.data ? <ContextPreviewResult preview={previewMutation.data} /> : null}
    </div>
  );
}

function ContextPreviewResult({ preview }: Readonly<{ preview: ContextPreview }>) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <MetricCard
          label="技能"
          value={preview.skill_id}
          detail={`节点 ${preview.node_id} · 模型 ${preview.model_name}`}
        />
        <MetricCard
          label="引用变量"
          value={formatCount(preview.referenced_variables.length)}
          detail={preview.referenced_variables.join(", ") || "模板当前没有引用变量"}
        />
        <MetricCard
          label="上下文占用"
          value={formatTokenCount(preview.context_report.total_tokens)}
          detail={`预算 ${formatTokenCount(preview.context_report.budget_limit)}`}
        />
        <MetricCard
          label="段落数"
          value={formatCount(preview.context_report.sections.length)}
          detail={`窗口 ${formatTokenCount(preview.context_report.model_context_window)}`}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.12fr_0.88fr]">
        <section className="panel-muted space-y-3 p-4">
          <header className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">最终 Prompt</h3>
            <p className="text-sm leading-6 text-text-secondary">
              渲染后的提示词预览。
            </p>
          </header>
          <pre className="mono-block whitespace-pre-wrap break-words">{preview.rendered_prompt}</pre>
        </section>

        <div className="space-y-4">
          <section className="panel-muted space-y-3 p-4">
            <header className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">上下文 Sections</h3>
              <p className="text-sm leading-6 text-text-secondary">
                查看上下文注入情况。
              </p>
            </header>
            {preview.context_report.sections.length > 0 ? (
              <div className="space-y-3">
                {preview.context_report.sections.map((section, index) => (
                  <ContextSectionCard key={`${section.type}-${index}`} section={section} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">暂无分节详情。</p>
            )}
          </section>

          <section className="panel-muted space-y-3 p-4">
            <header className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">变量快照</h3>
              <p className="text-sm leading-6 text-text-secondary">
                查看原始变量。
              </p>
            </header>
            <CodeBlock value={preview.variables} />
          </section>
        </div>
      </div>
    </div>
  );
}

function ContextSectionCard({ section }: Readonly<{ section: ContextPreviewSection }>) {
  const details = buildSectionDetail(section);

  return (
    <div className="rounded-2xl bg-muted shadow-sm p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-medium text-text-primary">
            {formatSectionLabel(section.type)}
          </p>
          <p className="text-xs uppercase tracking-[0.12em] text-text-secondary">
            {section.type}
          </p>
        </div>
        <StatusBadge
          status={resolveSectionTone(section.status)}
          label={formatSectionStatusLabel(section.status)}
        />
      </div>
      <div className="mt-3 space-y-1">
        {details.map((detail) => (
          <p key={`${section.type}-${detail}`} className="text-sm leading-6 text-text-secondary">
            {detail}
          </p>
        ))}
      </div>
    </div>
  );
}

function FeedbackMessage({
  tone,
  message,
}: Readonly<{
  tone: "danger";
  message: string;
}>) {
  return (
    <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
      {message}
    </div>
  );
}
