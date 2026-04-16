"use client";

import { useState, useRef, useCallback } from "react";

import type { DocumentTreeNode } from "@/features/studio/components/page/studio-page-support";
import type { StudioDocumentLiveSyncState } from "@/features/studio/components/document/studio-document-live-sync-support";

type MarkdownDocumentEditorProps = {
  documentPath: string | null;
  documentNode: DocumentTreeNode | null;
  content: string;
  isLoading?: boolean;
  saveNoun?: "文稿" | "文件";
  onChange: (content: string) => void;
  onSave: () => void;
  isSaving?: boolean;
  hasUnsavedChanges?: boolean;
  liveSyncState?: StudioDocumentLiveSyncState;
};

export function MarkdownDocumentEditor({
  documentPath,
  documentNode,
  content,
  isLoading = false,
  saveNoun = "文稿",
  onChange,
  onSave,
  isSaving = false,
  hasUnsavedChanges = false,
  liveSyncState,
}: Readonly<MarkdownDocumentEditorProps>) {
  const [viewMode, setViewMode] = useState<"edit" | "preview" | "split">("edit");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const surfaceState = resolveMarkdownDocumentSurfaceState({
    hasUnsavedChanges,
    isLoading,
    isSaving,
    liveSyncState,
    saveNoun,
  });

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "s") {
      event.preventDefault();
      if (!isLoading && !isSaving && hasUnsavedChanges) {
        onSave();
      }
    }
  }, [isLoading, isSaving, hasUnsavedChanges, onSave]);

  if (!documentPath) {
    return (
      <div className="flex items-center justify-center h-full bg-surface">
        <div className="text-center max-w-sm px-6">
          <div className="flex items-center justify-center w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-soft to-accent-primary/10 text-accent-primary">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 className="m-0 mb-2 font-serif text-xl font-bold text-text-primary">从左侧挑一份文稿</h3>
          <p className="m-0 text-sm text-text-tertiary leading-relaxed">设定、大纲、正文和附录都收在同一张写作纸面里，先选中文稿再开始进入正文。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-surface">
      <div className="absolute inset-0 opacity-[0.015] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.5%22_numOctaves%3D%224%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      
      <header className="relative z-10 flex shrink-0 items-center justify-between gap-3 px-4 py-2.5 bg-gradient-to-b from-elevated/96 to-muted border-b border-line-soft lg:px-5">
        <div className="absolute bottom-0 left-5 right-5 h-px bg-gradient-to-r from-transparent via-accent-primary to-transparent opacity-15" />
        <div className="flex min-w-0 flex-col gap-0.5">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="m-0 truncate font-serif text-[0.98rem] font-bold tracking-tight text-text-primary">{documentNode?.label ?? "未命名文档"}</h2>
            <span className={surfaceState.badgeClassName}>
              {surfaceState.badgeLabel}
            </span>
          </div>
          <p className="m-0 truncate text-[0.72rem] text-text-tertiary">{documentPath}</p>
          {surfaceState.detail ? (
            <p className={surfaceState.detailClassName}>
              {surfaceState.detail}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden sm:flex bg-surface-hover rounded-md p-0.5">
            {(["edit", "split", "preview"] as const).map((mode) => (
              <button
                key={mode}
                className={`inline-flex h-[26px] items-center justify-center px-2.5 border-none rounded-2xl text-[0.72rem] font-semibold cursor-pointer transition-all ${viewMode === mode ? "bg-elevated text-text-primary shadow-sm" : "bg-transparent text-text-tertiary hover:text-text-primary"}`}
                onClick={() => setViewMode(mode)}
                type="button"
              >
                {mode === "edit" ? "编辑" : mode === "split" ? "分栏" : "预览"}
              </button>
            ))}
          </div>
          <span className="hidden text-[0.68rem] font-medium text-text-tertiary lg:inline">Ctrl/⌘+S</span>
        </div>
      </header>
      
      <div
        className={`relative z-10 grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)] overflow-hidden ${viewMode === "split" ? "grid-cols-2 divide-x divide-line-soft" : "grid-cols-1"}`}
        data-mode={viewMode}
      >
        {viewMode !== "preview" ? (
          <section className="h-full min-h-0 min-w-0 overflow-hidden bg-transparent">
            <textarea
              ref={textareaRef}
              className="block h-full min-h-0 w-full resize-none overflow-y-auto border-none bg-transparent px-7 pt-7 pb-12 text-text-primary font-serif text-[0.98rem] leading-8 tracking-wide outline-none placeholder:text-text-tertiary placeholder:italic lg:px-10 lg:pt-8"
              value={content}
              readOnly={isLoading}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isLoading ? "正在载入文稿…" : "开始整理你的设定、章节或正文…"}
              spellCheck={false}
            />
          </section>
        ) : null}
        {viewMode !== "edit" ? (
          <section className="h-full min-h-0 min-w-0 overflow-hidden bg-gradient-to-r from-surface-hover to-transparent [background-size:1px_100%]">
            <div className="h-full min-h-0 overflow-y-auto">
              <MarkdownPreview content={content} />
            </div>
          </section>
        ) : null}
      </div>
      
      <footer aria-live="polite" className="flex shrink-0 items-center justify-between gap-3 px-4 py-1.5 bg-gradient-to-b from-muted to-elevated/80 border-t border-line-soft lg:px-5">
        <span className="text-xs text-text-tertiary">{content.length} 字符 · {content.split(/\s+/).filter(Boolean).length} 词</span>
        <span className={surfaceState.footerClassName}>
          {surfaceState.footerLabel}
        </span>
      </footer>
    </div>
  );
}

function resolveMarkdownDocumentSurfaceState(options: {
  hasUnsavedChanges: boolean;
  isLoading: boolean;
  isSaving: boolean;
  liveSyncState?: StudioDocumentLiveSyncState;
  saveNoun: "文稿" | "文件";
}) {
  if (options.isLoading) {
    return {
      badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-warning/15 text-accent-warning",
      badgeLabel: "载入中",
      detail: null,
      detailClassName: "m-0 text-[0.68rem] text-text-tertiary",
      footerClassName: "text-xs text-accent-warning",
      footerLabel: `正在载入${options.saveNoun}`,
    };
  }
  if (options.isSaving) {
    return {
      badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-primary/10 text-accent-primary animate-pulse",
      badgeLabel: "保存中",
      detail: null,
      detailClassName: "m-0 text-[0.68rem] text-text-tertiary",
      footerClassName: "text-xs text-accent-primary",
      footerLabel: `${options.saveNoun}保存中…`,
    };
  }
  if (options.liveSyncState?.status === "stale_remote") {
    return {
      badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-warning/15 text-accent-warning",
      badgeLabel: "待重载",
      detail: options.liveSyncState.detail,
      detailClassName: "m-0 text-[0.68rem] text-accent-warning",
      footerClassName: "text-xs text-accent-warning",
      footerLabel: "远端已有新版本，当前保留你的本地草稿",
    };
  }
  if (options.hasUnsavedChanges) {
    return {
      badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-warning/15 text-accent-warning",
      badgeLabel: "未保存",
      detail: null,
      detailClassName: "m-0 text-[0.68rem] text-text-tertiary",
      footerClassName: "text-xs text-accent-warning",
      footerLabel: `${options.saveNoun}未保存`,
    };
  }
  if (options.liveSyncState?.status === "writing") {
    return {
      badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-primary/10 text-accent-primary animate-pulse",
      badgeLabel: "写入中",
      detail: options.liveSyncState.detail,
      detailClassName: "m-0 text-[0.68rem] text-accent-primary",
      footerClassName: "text-xs text-accent-primary",
      footerLabel: "助手正在改写当前文稿…",
    };
  }
  if (options.liveSyncState?.status === "synced") {
    return {
      badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-primary/10 text-accent-primary ring-4 ring-accent-soft",
      badgeLabel: "刚更新",
      detail: options.liveSyncState.detail,
      detailClassName: "m-0 text-[0.68rem] text-accent-primary",
      footerClassName: "text-xs text-accent-primary",
      footerLabel: "助手写入已自动同步",
    };
  }
  return {
    badgeClassName: "shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] bg-accent-soft text-accent-primary",
    badgeLabel: "已同步",
    detail: null,
    detailClassName: "m-0 text-[0.68rem] text-text-tertiary",
    footerClassName: "text-xs text-text-tertiary",
    footerLabel: `${options.saveNoun}已同步`,
  };
}

function MarkdownPreview({ content }: { content: string }) {
  const renderMarkdown = (text: string): string => {
    let html = text
      .replace(/^### (.*$)/gim, "<h3>$1</h3>")
      .replace(/^## (.*$)/gim, "<h2>$1</h2>")
      .replace(/^# (.*$)/gim, "<h1>$1</h1>")
      .replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>")
      .replace(/\*\*(.*)\*\*/gim, "<strong>$1</strong>")
      .replace(/\*(.*)\*/gim, "<em>$1</em>")
      .replace(/`([^`]+)`/gim, "<code>$1</code>")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/gim, '<img alt="$1" src="$2" />')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/^\- (.*$)/gim, "<li>$1</li>")
      .replace(/^\d+\. (.*$)/gim, "<li>$1</li>")
      .replace(/\n/gim, "<br>");

    html = html.replace(/```(\w*)\n([\s\S]*?)```/gim, (_, lang, code) => {
      return `<pre class="my-3 px-4 py-3 rounded-lg bg-muted text-text-primary font-mono text-[0.82rem] leading-relaxed overflow-x-auto border border-line-soft" data-lang="${lang}"><code>${code.trim()}</code></pre>`;
    });

    return html;
  };

  return (
    <div
      className="box-border w-full max-w-[820px] mx-auto px-6 py-8 text-text-primary font-serif text-base leading-8 tracking-wide [&_h1]:my-6 [&_h1]:mb-3 [&_h1]:text-[1.7rem] [&_h1]:font-bold [&_h1]:tracking-tight [&_h1]:leading-tight [&_h1:first-child]:mt-0 [&_h2]:my-5 [&_h2]:mb-2.5 [&_h2]:text-[1.35rem] [&_h2]:font-bold [&_h2]:leading-relaxed [&_h3]:my-4 [&_h3]:mb-2 [&_h3]:text-[1.1rem] [&_h3]:font-semibold [&_h3]:leading-relaxed [&_p]:my-3 [&_blockquote]:my-3.5 [&_blockquote]:py-0.5 [&_blockquote]:pl-3.5 [&_blockquote]:border-l-2 [&_blockquote]:border-accent-primary [&_blockquote]:text-text-secondary [&_blockquote]:italic [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:bg-surface-hover [&_code]:text-accent-danger [&_code]:font-mono [&_code]:text-[0.88em] [&_a]:text-accent-primary [&_a]:underline [&_a]:underline-offset-2 [&_ul]:my-3 [&_ol]:my-3 [&_ul]:pl-5 [&_ol]:pl-5 [&_li]:my-1 [&_li]:pl-1"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}
