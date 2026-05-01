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
      <div className="mde-empty">
        <div className="mde-empty__card">
          <div className="mde-empty__icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 className="mde-empty__title">从左侧挑一份文稿</h3>
          <p className="mde-empty__desc">
            设定、大纲、正文和附录都收在同一张写作纸面里，先选中文稿再开始进入正文。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mde-root">
      {/* 编辑器头部 */}
      <header className="mde-header">
        <div className="mde-header__left">
          <h2 className="mde-header__title">{documentNode?.label ?? "未命名文档"}</h2>
          <span className={`mde-header__badge ${surfaceState.badgeClass}`}>
            {surfaceState.badgeLabel}
          </span>
        </div>
        <div className="mde-header__right">
          <div className="mde-viewtabs">
            {(["edit", "split", "preview"] as const).map((mode) => (
              <button
                key={mode}
                className={`mde-viewtabs__btn ${viewMode === mode ? "mde-viewtabs__btn--active" : ""}`}
                onClick={() => setViewMode(mode)}
                type="button"
              >
                {mode === "edit" ? "编辑" : mode === "split" ? "分栏" : "预览"}
              </button>
            ))}
          </div>
          <span className="mde-header__shortcut">Ctrl/⌘+S</span>
        </div>
      </header>

      {/* 编辑区域 */}
      <div
        className={`mde-body ${viewMode === "split" ? "mde-body--split" : ""}`}
        data-mode={viewMode}
      >
        {viewMode !== "preview" ? (
          <section className="mde-edit">
            <textarea
              ref={textareaRef}
              className="mde-edit__textarea"
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
          <section className="mde-preview">
            <div className="mde-preview__scroll">
              <MarkdownPreview content={content} />
            </div>
          </section>
        ) : null}
      </div>

      {/* 底部状态栏 */}
      <footer className="mde-footer">
        <span className="mde-footer__stats">
          {content.length} 字符 · {content.split(/\s+/).filter(Boolean).length} 词
        </span>
        <span className={`mde-footer__status ${surfaceState.footerClass}`}>
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
      badgeClass: "mde-badge--warning",
      badgeLabel: "载入中",
      footerClass: "mde-footer__status--warning",
      footerLabel: `正在载入${options.saveNoun}`,
    };
  }
  if (options.isSaving) {
    return {
      badgeClass: "mde-badge--primary",
      badgeLabel: "保存中",
      footerClass: "mde-footer__status--primary",
      footerLabel: `${options.saveNoun}保存中…`,
    };
  }
  if (options.liveSyncState?.status === "stale_remote") {
    return {
      badgeClass: "mde-badge--warning",
      badgeLabel: "待重载",
      footerClass: "mde-footer__status--warning",
      footerLabel: "远端已有新版本，当前保留你的本地草稿",
    };
  }
  if (options.hasUnsavedChanges) {
    return {
      badgeClass: "mde-badge--warning",
      badgeLabel: "未保存",
      footerClass: "mde-footer__status--warning",
      footerLabel: `${options.saveNoun}未保存`,
    };
  }
  if (options.liveSyncState?.status === "writing") {
    return {
      badgeClass: "mde-badge--primary",
      badgeLabel: "写入中",
      footerClass: "mde-footer__status--primary",
      footerLabel: "助手正在改写当前文稿…",
    };
  }
  if (options.liveSyncState?.status === "synced") {
    return {
      badgeClass: "mde-badge--success",
      badgeLabel: "刚更新",
      footerClass: "mde-footer__status--success",
      footerLabel: "助手写入已自动同步",
    };
  }
  return {
    badgeClass: "mde-badge--muted",
    badgeLabel: "已同步",
    footerClass: "mde-footer__status--muted",
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
      return `<pre class="mde-pre" data-lang="${lang}"><code>${code.trim()}</code></pre>`;
    });

    return html;
  };

  return (
    <div
      className="mde-preview__content"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}
