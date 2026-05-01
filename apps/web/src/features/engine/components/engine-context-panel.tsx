"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
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
    <div className="space-y-3">
      <div className="rounded p-4" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
        <div className="space-y-3">
          <div className="grid gap-3 grid-cols-2">
            <label className="block space-y-1">
              <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>node_id</span>
              <input
                className="w-full px-3 py-2 rounded text-[12px] outline-none"
                style={{ background: "var(--bg-muted)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
                value={nodeId}
                onChange={(event) => setNodeId(event.target.value)}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>chapter_number</span>
              <input
                className="w-full px-3 py-2 rounded text-[12px] outline-none"
                style={{ background: "var(--bg-muted)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
                inputMode="numeric"
                value={chapterNumber}
                onChange={(event) => setChapterNumber(event.target.value)}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
              />
            </label>
          </div>

          <label className="block space-y-1">
            <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>extra_inject JSON（可选）</span>
            <textarea
              className="w-full px-3 py-2 rounded text-[12px] outline-none min-h-[100px] resize-y"
              style={{ background: "var(--bg-muted)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
              placeholder={EXTRA_INJECT_PLACEHOLDER}
              value={extraInjectText}
              onChange={(event) => setExtraInjectText(event.target.value)}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
            />
          </label>

          <EngineContextStyleReferenceHelper
            extraInjectText={extraInjectText}
            projectId={projectId}
            onApply={setExtraInjectText}
          />

          <button
            className="px-4 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40"
            style={{ background: "var(--accent-primary)", color: "var(--bg-canvas)" }}
            disabled={previewMutation.isPending || !nodeId.trim()}
            onClick={() => previewMutation.mutate()}
          >
            {previewMutation.isPending ? "预览中..." : "预览上下文"}
          </button>

          {previewMutation.error ? (
            <FeedbackMessage tone="danger" message={getErrorMessage(previewMutation.error)} />
          ) : null}
        </div>
      </div>

      {previewMutation.data ? <ContextPreviewResult preview={previewMutation.data} /> : null}
    </div>
  );
}

function ContextPreviewResult({ preview }: Readonly<{ preview: ContextPreview }>) {
  return (
    <div className="space-y-3">
      <div className="grid gap-2 grid-cols-2 md:grid-cols-4">
        <MetricItem label="技能" value={preview.skill_id} detail={`节点 ${preview.node_id} · 模型 ${preview.model_name}`} />
        <MetricItem label="引用变量" value={formatCount(preview.referenced_variables.length)} detail={preview.referenced_variables.join(", ") || "模板当前没有引用变量"} />
        <MetricItem label="上下文占用" value={formatTokenCount(preview.context_report.total_tokens)} detail={`预算 ${formatTokenCount(preview.context_report.budget_limit)}`} />
        <MetricItem label="段落数" value={formatCount(preview.context_report.sections.length)} detail={`窗口 ${formatTokenCount(preview.context_report.model_context_window)}`} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.12fr_0.88fr]">
        <div className="rounded p-4" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
          <h3 className="text-[12px] font-medium mb-2" style={{ color: "var(--text-tertiary)" }}>最终 Prompt</h3>
          <pre className="whitespace-pre-wrap break-words text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{preview.rendered_prompt}</pre>
        </div>

        <div className="space-y-3">
          <div className="rounded p-4" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
            <h3 className="text-[12px] font-medium mb-2" style={{ color: "var(--text-tertiary)" }}>上下文 Sections</h3>
            {preview.context_report.sections.length > 0 ? (
              <div className="space-y-2">
                {preview.context_report.sections.map((section, index) => (
                  <ContextSectionCard key={`${section.type}-${index}`} section={section} />
                ))}
              </div>
            ) : (
              <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>暂无分节详情。</p>
            )}
          </div>

          <div className="rounded p-4" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
            <h3 className="text-[12px] font-medium mb-2" style={{ color: "var(--text-tertiary)" }}>变量快照</h3>
            <CodeBlock value={preview.variables} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ContextSectionCard({ section }: Readonly<{ section: ContextPreviewSection }>) {
  const details = buildSectionDetail(section);

  return (
    <div className="rounded p-2.5" style={{ background: "var(--bg-muted)" }}>
      <div className="flex items-center justify-between gap-3">
        <div className="space-y-0.5">
          <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
            {formatSectionLabel(section.type)}
          </p>
          <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
            {section.type}
          </p>
        </div>
        <StatusPill tone={resolveSectionTone(section.status)} label={formatSectionStatusLabel(section.status)} />
      </div>
      <div className="mt-2 space-y-0.5">
        {details.map((detail) => (
          <p key={`${section.type}-${detail}`} className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
            {detail}
          </p>
        ))}
      </div>
    </div>
  );
}

function MetricItem({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded p-3" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
      <p className="text-[10px] mb-1" style={{ color: "var(--text-tertiary)" }}>{label}</p>
      <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>{value}</p>
      {detail ? <p className="text-[10px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>{detail}</p> : null}
    </div>
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

function FeedbackMessage({
  tone,
  message,
}: Readonly<{
  tone: "danger";
  message: string;
}>) {
  return (
    <div className="rounded px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
      {message}
    </div>
  );
}
