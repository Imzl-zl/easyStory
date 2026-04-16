"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { EChartsType } from "echarts/core";
import * as echarts from "echarts/core";
import { GraphChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { GridComponent, TooltipComponent } from "echarts/components";

import type {
  JsonGraphSourceSummary,
  JsonRelationGraphModel,
} from "@/features/studio/components/document/json-document-support";
import {
  buildJsonRelationGraphOption,
  isValidJsonRelationGraphSelection,
  resolveJsonRelationGraphInspector,
  type JsonRelationGraphSelection,
} from "@/features/studio/components/document/json-relation-graph-support";

echarts.use([CanvasRenderer, GraphChart, GridComponent, TooltipComponent]);

type JsonRelationGraphProps = {
  activeSourceLabel: string;
  graph: JsonRelationGraphModel;
  sourceSummary: JsonGraphSourceSummary;
};

export function JsonRelationGraph({
  activeSourceLabel,
  graph,
  sourceSummary,
}: Readonly<JsonRelationGraphProps>) {
  const [selection, setSelection] = useState<JsonRelationGraphSelection>(null);
  const [rawSelectionKey, setRawSelectionKey] = useState<string | null>(null);
  const activeSelection = useMemo(
    () => (isValidJsonRelationGraphSelection(graph, selection) ? selection : null),
    [graph, selection],
  );
  const inspector = useMemo(
    () => resolveJsonRelationGraphInspector(graph, activeSelection),
    [activeSelection, graph],
  );
  const selectionKey = activeSelection ? `${activeSelection.kind}:${activeSelection.id}` : null;
  const showRawContent = selectionKey !== null && rawSelectionKey === selectionKey;

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden">
      <header className="flex flex-wrap items-center gap-2 border-b border-line-soft px-5 py-3">
        <span className="rounded-full bg-accent-info/10 px-2.5 py-1 text-[11px] text-accent-info">
          当前文件：{activeSourceLabel}
        </span>
        <StatChip label="人物" value={sourceSummary.characterCount} />
        <StatChip label="势力" value={sourceSummary.factionCount} />
        <StatChip label="人物关系" value={sourceSummary.characterRelationCount} />
        <StatChip label="势力关系" value={sourceSummary.factionRelationCount} />
        <StatChip label="隶属" value={sourceSummary.membershipCount} />
        <span className="ml-auto rounded-full bg-accent-soft px-2.5 py-1 text-[11px] text-accent-primary">
          只读图预览
        </span>
      </header>
      <div className="relative min-h-0 overflow-hidden">
        <JsonRelationGraphCanvas
          graph={graph}
          selection={activeSelection}
          onSelect={(nextSelection) => {
            setSelection((currentSelection) =>
              currentSelection?.kind === nextSelection.kind && currentSelection.id === nextSelection.id
                ? null
                : nextSelection,
            );
          }}
        />
        {inspector ? (
          <JsonRelationGraphInspectorPanel
            inspector={inspector}
            showRawContent={showRawContent}
            onClear={() => setSelection(null)}
            onToggleRaw={() => {
              if (!selectionKey) {
                return;
              }
              setRawSelectionKey((current) => (current === selectionKey ? null : selectionKey));
            }}
          />
        ) : (
          <JsonRelationGraphHint />
        )}
      </div>
    </div>
  );
}

type JsonRelationGraphCanvasProps = {
  graph: JsonRelationGraphModel;
  onSelect: (selection: NonNullable<JsonRelationGraphSelection>) => void;
  selection: JsonRelationGraphSelection;
};

function JsonRelationGraphCanvas({
  graph,
  onSelect,
  selection,
}: Readonly<JsonRelationGraphCanvasProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<EChartsType | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = chartRef.current ?? echarts.init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(buildJsonRelationGraphOption(graph, selection), true);

    const handleClick = (params: unknown) => {
      const payload = isGraphClickPayload(params) ? params : null;
      if (!payload) {
        return;
      }
      const id = typeof payload?.data?.id === "string" ? payload.data.id : null;
      if (!id) {
        return;
      }
      if (payload.dataType === "node") {
        onSelect({ id, kind: "node" });
        return;
      }
      if (payload.dataType === "edge") {
        onSelect({ id, kind: "edge" });
      }
    };

    chart.off("click");
    chart.on("click", handleClick as never);
    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(container);
    return () => {
      chart.off("click", handleClick);
      resizeObserver.disconnect();
    };
  }, [graph, onSelect, selection]);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return <div className="h-full w-full bg-canvas" ref={containerRef} />;
}

function StatChip({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <span className="rounded-full bg-muted shadow-xs px-2.5 py-1 text-[11px] text-text-secondary">
      {label} {value}
    </span>
  );
}

function JsonRelationGraphHint() {
  return (
    <div className="pointer-events-none absolute inset-x-4 bottom-4 z-10 flex justify-center">
      <div className="flex max-w-[560px] items-center gap-3 rounded-2xl bg-glass shadow-glass px-4 py-3 shadow-md backdrop-blur">
        <span className="rounded-full bg-accent-primary/10 px-2.5 py-1 text-[11px] font-medium text-accent-primary">
          关系总览
        </span>
        <p className="m-0 text-[12px] leading-6 text-text-secondary">
          点击节点或连线查看详情。缩放和平移只影响当前视图，不会改写任何关系。
        </p>
      </div>
    </div>
  );
}

function JsonRelationGraphInspectorPanel({
  inspector,
  onClear,
  onToggleRaw,
  showRawContent,
}: Readonly<{
  inspector: NonNullable<ReturnType<typeof resolveJsonRelationGraphInspector>>;
  onClear: () => void;
  onToggleRaw: () => void;
  showRawContent: boolean;
}>) {
  return (
    <aside className="absolute right-4 top-4 z-10 w-[min(360px,calc(100%-2rem))] max-h-[calc(100%-2rem)]">
      <div className="flex max-h-full flex-col overflow-hidden rounded-[30px] bg-glass shadow-glass-heavy shadow-lg backdrop-blur-xl">
        <div
          className="relative overflow-hidden border-b border-line-soft px-5 py-5"
          style={{
            background: `linear-gradient(180deg, color-mix(in srgb, ${inspector.accentColor} 14%, white) 0%, rgba(255,252,247,0.96) 72%)`,
          }}
        >
          <div className="absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-line-strong to-transparent" />
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <span
                className="inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold tracking-[0.12em]"
                style={{
                  backgroundColor: `color-mix(in srgb, ${inspector.accentColor} 14%, white)`,
                  color: inspector.accentColor,
                }}
              >
                {inspector.kindLabel}
              </span>
              <h3 className="mt-3 truncate font-serif text-[1.08rem] font-bold tracking-[-0.01em] text-text-primary">
                {inspector.title}
              </h3>
              <p className="mt-1 text-[12px] leading-5 text-text-secondary">
                {inspector.subtitle}
              </p>
            </div>
            <button
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface shadow-xs text-text-secondary transition hover:bg-elevated hover:text-text-primary"
              type="button"
              onClick={onClear}
            >
              ×
            </button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {inspector.badges.map((badge) => (
              <span
                className="rounded-full bg-muted shadow-xs px-2.5 py-1 text-[11px] text-text-secondary"
                key={badge}
              >
                {badge}
              </span>
            ))}
          </div>
        </div>

        <div className="min-h-0 overflow-y-auto px-5 py-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {inspector.facts.map((fact, index) => (
              <div
                className={`rounded-2xl bg-muted shadow-sm px-3.5 py-3  ${inspector.facts.length % 2 === 1 && index === inspector.facts.length - 1 ? "sm:col-span-2" : ""}`}
                key={fact.label}
              >
                <p className="m-0 text-[11px] font-medium tracking-[0.06em] text-text-secondary">
                  {fact.label}
                </p>
                <p className="mt-1.5 text-[13px] leading-6 text-text-primary">
                  {fact.value}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-2xl bg-muted shadow-sm px-4 py-3.5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="m-0 text-[11px] font-medium tracking-[0.08em] text-text-secondary">
                  原始字段
                </p>
                <p className="mt-1 text-[12px] leading-5 text-text-secondary">
                  默认不展开，只有核对结构化字段时再查看。
                </p>
              </div>
              <button
                className="shrink-0 rounded-full bg-surface shadow-xs px-3 py-1.5 text-[11px] font-medium text-text-secondary transition hover:text-text-primary"
                type="button"
                onClick={onToggleRaw}
              >
                {showRawContent ? "收起字段" : "查看字段"}
              </button>
            </div>
            {showRawContent ? (
              <div className="mt-3 rounded-2xl bg-muted shadow-sm p-3">
                <p className="m-0 text-[11px] font-medium tracking-[0.08em] text-text-secondary">
                  {inspector.rawTitle}
                </p>
                <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-2xl bg-glass px-3 py-3 text-[11px] leading-5 text-text-primary">
                  {inspector.rawContent}
                </pre>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </aside>
  );
}

function isGraphClickPayload(
  value: unknown,
): value is { data?: { id?: unknown } | null; dataType?: string } {
  return typeof value === "object" && value !== null;
}
