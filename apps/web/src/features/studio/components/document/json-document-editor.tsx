"use client";

import { useCallback, useDeferredValue, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { JsonRelationGraph } from "@/features/studio/components/document/json-relation-graph";
import {
  buildStudioJsonPreviewState,
  listStudioJsonPreviewSourcePaths,
  resolveStudioJsonPreviewMode,
} from "@/features/studio/components/document/json-document-support";
import type { StudioDocumentEditorProps } from "@/features/studio/components/document/studio-document-editor-types";
import { getProjectDocument } from "@/lib/api/projects";
import { getErrorMessage } from "@/lib/api/client";

export function JsonDocumentEditor({
  availableDocumentPaths,
  content,
  documentNode,
  documentPath,
  hasUnsavedChanges = false,
  isLoading = false,
  isSaving = false,
  onChange,
  onSave,
  projectId,
  saveNoun = "文件",
}: Readonly<StudioDocumentEditorProps>) {
  const previewMode = resolveStudioJsonPreviewMode(documentPath);
  const [viewMode, setViewMode] = useState<"edit" | "preview" | "split">(
    previewMode === "graph" ? "preview" : "split",
  );
  const deferredContent = useDeferredValue(content);
  const previewSourcePaths = useMemo(
    () => listStudioJsonPreviewSourcePaths(documentPath, availableDocumentPaths),
    [availableDocumentPaths, documentPath],
  );
  const siblingSourcePaths = useMemo(
    () => previewSourcePaths.filter((path) => path !== documentPath),
    [documentPath, previewSourcePaths],
  );

  const previewSourcesQuery = useQuery({
    enabled: previewMode === "graph" && siblingSourcePaths.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        siblingSourcePaths.map(async (path) => [path, (await getProjectDocument(projectId, path)).content] as const),
      );
      return Object.fromEntries(entries);
    },
    queryKey: ["studio-json-preview", projectId, siblingSourcePaths],
    refetchOnWindowFocus: false,
  });

  const previewContents = useMemo(
    () => Object.fromEntries(previewSourcePaths.map((path) => [
      path,
      path === documentPath ? deferredContent : (previewSourcesQuery.data?.[path] ?? ""),
    ])),
    [deferredContent, documentPath, previewSourcePaths, previewSourcesQuery.data],
  );
  const previewState = useMemo(
    () => buildStudioJsonPreviewState(documentPath, previewContents),
    [documentPath, previewContents],
  );

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "s") {
      event.preventDefault();
      if (!isLoading && !isSaving && hasUnsavedChanges) {
        onSave();
      }
    }
  }, [hasUnsavedChanges, isLoading, isSaving, onSave]);

  if (!documentPath) {
    return (
      <div className="flex h-full items-center justify-center bg-[#fefdfb]">
        <div className="max-w-sm px-6 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[rgba(90,122,107,0.12)] to-[rgba(196,167,108,0.08)] text-[var(--accent-primary)]">
            <svg fill="none" height="48" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" width="48">
              <path d="M8 3h7l5 5v13H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
              <path d="M15 3v5h5" />
              <path d="M10 12h7" />
              <path d="M10 16h5" />
            </svg>
          </div>
          <h3 className="m-0 mb-2 font-serif text-xl font-bold text-[var(--text-primary)]">从左侧挑一份 JSON</h3>
          <p className="m-0 text-sm leading-relaxed text-[var(--text-muted)]">
            数据层会在这里提供结构化编辑和图预览，其它 JSON 也会保留格式化查看。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-[#fefdfb]">
      <div className="pointer-events-none absolute inset-0 opacity-[0.015] [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.5%22_numOctaves%3D%224%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />

      <header className="relative z-10 flex shrink-0 items-center justify-between gap-3 border-b border-[rgba(44,36,22,0.05)] bg-gradient-to-b from-white/96 to-[rgba(254,253,251,0.76)] px-4 py-2.5 lg:px-5">
        <div className="absolute bottom-0 left-5 right-5 h-px bg-gradient-to-r from-transparent via-[var(--accent-primary)] to-transparent opacity-15" />
        <div className="flex min-w-0 flex-col gap-0.5">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="m-0 truncate font-serif text-[0.98rem] font-bold tracking-tight text-[var(--text-primary)]">
              {documentNode?.label ?? "未命名 JSON"}
            </h2>
            <span className="shrink-0 rounded-full bg-[rgba(35,96,137,0.08)] px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] text-[#245b82]">
              {previewMode === "graph" ? "图预览" : "JSON 预览"}
            </span>
            {previewMode === "graph" ? (
              <span className="shrink-0 rounded-full bg-[rgba(196,167,108,0.12)] px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] text-[var(--accent-warning)]">
                整组数据层总览
              </span>
            ) : null}
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] ${hasUnsavedChanges ? "bg-[rgba(196,167,108,0.14)] text-[var(--accent-warning)]" : "bg-[rgba(90,122,107,0.08)] text-[var(--accent-primary)]"}`}>
              {hasUnsavedChanges ? "未保存" : "已同步"}
            </span>
          </div>
          <p className="m-0 truncate text-[0.72rem] text-[var(--text-muted)]">{documentPath}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden rounded-md bg-[rgba(44,36,22,0.04)] p-0.5 sm:flex">
            {(["edit", "split", "preview"] as const).map((mode) => (
              <button
                className={`inline-flex h-[26px] items-center justify-center rounded-[5px] border-none px-2.5 text-[0.72rem] font-semibold transition-all ${viewMode === mode ? "bg-white text-[var(--text-primary)] shadow-[0_1px_3px_rgba(44,36,22,0.08)]" : "bg-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"}`}
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
              >
                {mode === "edit" ? "编辑" : mode === "split" ? "分栏" : "预览"}
              </button>
            ))}
          </div>
          <span className="hidden text-[0.68rem] font-medium text-[var(--text-muted)] lg:inline">Ctrl/⌘+S</span>
        </div>
      </header>

      <div
        className={`relative z-10 grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)] overflow-hidden ${viewMode === "split" ? "grid-cols-2 divide-x divide-[rgba(44,36,22,0.05)]" : "grid-cols-1"}`}
      >
        {viewMode !== "preview" ? (
          <section className="h-full min-h-0 min-w-0 overflow-hidden">
            <textarea
              className="block h-full min-h-0 w-full resize-none overflow-y-auto border-none bg-transparent px-7 pt-7 pb-12 font-mono text-[0.88rem] leading-7 tracking-[0.01em] text-[var(--text-primary)] outline-none placeholder:text-[#9f9385] lg:px-10 lg:pt-8"
              placeholder={isLoading ? "正在载入 JSON…" : "写入合法 JSON。数据层文稿会自动生成图预览，其它 JSON 会保留格式化查看。"}
              readOnly={isLoading}
              spellCheck={false}
              value={content}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={handleKeyDown}
            />
          </section>
        ) : null}
        {viewMode !== "edit" ? (
          <section className="h-full min-h-0 min-w-0 overflow-hidden bg-gradient-to-r from-[rgba(44,36,22,0.02)] to-transparent">
            <div className="h-full min-h-0 overflow-y-auto">
              <JsonPreviewPanel
                errorMessage={previewSourcesQuery.error ? getErrorMessage(previewSourcesQuery.error) : null}
                isLoadingGraphSources={previewMode === "graph" && siblingSourcePaths.length > 0 && previewSourcesQuery.isLoading && !previewSourcesQuery.data}
                previewMode={previewMode}
                previewState={previewState}
              />
            </div>
          </section>
        ) : null}
      </div>

      <footer
        aria-live="polite"
        className="flex shrink-0 items-center justify-between gap-3 border-t border-[rgba(44,36,22,0.05)] bg-gradient-to-b from-[rgba(254,253,251,0.5)] to-white/80 px-4 py-1.5 lg:px-5"
      >
        <span className="text-xs text-[var(--text-muted)]">
          {content.length} 字符 · {content.split("\n").length} 行
        </span>
        <span className="hidden text-xs text-[var(--text-muted)] lg:inline">
          {previewMode === "graph" ? "当前预览会读取同目录下的人物、势力、人物关系、势力关系和隶属 JSON。" : "当前预览只展示这份 JSON 本身。"}
        </span>
        <span className={`text-xs ${isLoading || hasUnsavedChanges ? "text-[var(--accent-warning)]" : "text-[var(--text-muted)]"}`}>
          {isLoading ? `正在载入${saveNoun}` : hasUnsavedChanges ? `${saveNoun}未保存` : `${saveNoun}已同步`}
        </span>
      </footer>
    </div>
  );
}

function JsonPreviewPanel({
  errorMessage,
  isLoadingGraphSources,
  previewMode,
  previewState,
}: Readonly<{
  errorMessage: string | null;
  isLoadingGraphSources: boolean;
  previewMode: "graph" | "raw" | null;
  previewState: ReturnType<typeof buildStudioJsonPreviewState>;
}>) {
  if (errorMessage) {
    return (
      <JsonPreviewIssueState
        description={errorMessage}
        title="读取 JSON 预览依赖失败"
      />
    );
  }
  if (previewMode === "graph" && isLoadingGraphSources) {
    return (
      <JsonPreviewEmptyState
        description="正在读取同目录下的人物、势力、人物关系、势力关系和隶属数据…"
        title="准备图预览"
      />
    );
  }
  if (!previewState) {
    return (
      <JsonPreviewEmptyState
        description="当前文件不是 JSON 文稿，预览不会在这里渲染。"
        title="当前文稿不支持 JSON 预览"
      />
    );
  }
  if (previewState.kind === "graph") {
    if (previewState.status === "ready") {
      return (
        <JsonRelationGraph
          activeSourceLabel={previewState.activeSourceLabel}
          graph={previewState.graph}
          sourceSummary={previewState.sourceSummary}
        />
      );
    }
    if (previewState.status === "error") {
      return (
        <JsonPreviewIssueState
          description={`当前 ${previewState.activeSourceLabel} 数据有结构错误，修正后图预览会立即恢复。`}
          issues={previewState.issues}
          sourceSummary={previewState.sourceSummary}
          title="图预览暂时无法生成"
        />
      );
    }
    return (
      <JsonPreviewEmptyState
        description={previewState.message}
        sourceSummary={previewState.sourceSummary}
        title={`${previewState.activeSourceLabel} 还没有数据`}
      />
    );
  }
  if (previewState.status === "ready") {
    return <JsonRawPreview content={previewState.formattedContent} />;
  }
  if (previewState.status === "error") {
    return (
      <JsonPreviewIssueState
        description="先把当前文件修成合法 JSON，右侧格式化预览才会恢复。"
        issues={previewState.issues}
        title="JSON 解析失败"
      />
    );
  }
  return (
    <JsonPreviewEmptyState
      description={previewState.message}
      title="当前 JSON 还是空的"
    />
  );
}

function JsonPreviewIssueState({
  description,
  issues = [],
  sourceSummary,
  title,
}: Readonly<{
  description: string;
  issues?: ReadonlyArray<{ message: string; path: string }>;
  sourceSummary?: {
    characterCount: number;
    characterRelationCount: number;
    factionCount: number;
    factionRelationCount: number;
    membershipCount: number;
  };
  title: string;
}>) {
  return (
    <div className="mx-auto flex h-full max-w-[960px] flex-col px-6 py-8 lg:px-8">
      <h3 className="m-0 font-serif text-[1.2rem] font-bold text-[var(--text-primary)]">{title}</h3>
      <p className="mt-2 text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
      {sourceSummary ? <JsonSourceSummary summary={sourceSummary} /> : null}
      <ul className="mt-4 space-y-3">
        {issues.map((issue) => (
          <li
            className="rounded-[18px] border border-[rgba(154,74,61,0.16)] bg-[rgba(255,243,240,0.92)] px-4 py-3"
            key={`${issue.path}-${issue.message}`}
          >
            <p className="m-0 text-[12px] font-semibold text-[#8c3e2e]">{issue.path}</p>
            <p className="mt-1 text-[12px] leading-5 text-[#6f4b41]">{issue.message}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function JsonPreviewEmptyState({
  description,
  sourceSummary,
  title,
}: Readonly<{
  description: string;
  sourceSummary?: {
    characterCount: number;
    characterRelationCount: number;
    factionCount: number;
    factionRelationCount: number;
    membershipCount: number;
  };
  title: string;
}>) {
  return (
    <div className="flex h-full items-center justify-center px-6 py-10">
      <div className="max-w-[520px] rounded-[28px] border border-[rgba(101,92,82,0.08)] bg-[linear-gradient(180deg,rgba(255,253,249,0.98)_0%,rgba(248,244,236,0.95)_100%)] px-7 py-7 shadow-[0_18px_46px_rgba(58,45,29,0.08)]">
        <h3 className="m-0 font-serif text-[1.35rem] font-bold text-[var(--text-primary)]">{title}</h3>
        <p className="mt-2 text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
        {sourceSummary ? <JsonSourceSummary summary={sourceSummary} /> : null}
      </div>
    </div>
  );
}

function JsonSourceSummary({
  summary,
}: Readonly<{
  summary: {
    characterCount: number;
    characterRelationCount: number;
    factionCount: number;
    factionRelationCount: number;
    membershipCount: number;
  };
}>) {
  const items = [
    ["人物", summary.characterCount],
    ["势力", summary.factionCount],
    ["人物关系", summary.characterRelationCount],
    ["势力关系", summary.factionRelationCount],
    ["隶属", summary.membershipCount],
  ] as const;
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {items.map(([label, value]) => (
        <span
          className="rounded-full border border-[rgba(101,92,82,0.12)] bg-white/88 px-2.5 py-1 text-[11px] text-[var(--text-secondary)]"
          key={label}
        >
          {label} {value}
        </span>
      ))}
    </div>
  );
}

function JsonRawPreview({ content }: Readonly<{ content: string }>) {
  return (
    <div className="mx-auto h-full max-w-[920px] px-6 py-8 lg:px-8">
      <pre className="min-h-full overflow-x-auto whitespace-pre-wrap break-words rounded-[24px] border border-[rgba(44,36,22,0.06)] bg-[rgba(255,252,247,0.96)] px-5 py-5 font-mono text-[12px] leading-6 text-[var(--text-primary)] shadow-[0_18px_44px_rgba(58,45,29,0.06)]">
        {content}
      </pre>
    </div>
  );
}
