"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";
import styles from "./markdown-document-editor.module.css";

type MarkdownDocumentEditorProps = {
  documentPath: string | null;
  documentNode: DocumentTreeNode | null;
  content: string;
  onChange: (content: string) => void;
  onSave: () => void;
  isSaving?: boolean;
  hasUnsavedChanges?: boolean;
};

export function MarkdownDocumentEditor({
  documentPath,
  documentNode,
  content,
  onChange,
  onSave,
  isSaving = false,
  hasUnsavedChanges = false,
}: Readonly<MarkdownDocumentEditorProps>) {
  const [viewMode, setViewMode] = useState<"edit" | "preview" | "split">("edit");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "s") {
      event.preventDefault();
      if (!isSaving && hasUnsavedChanges) {
        onSave();
      }
    }
  }, [isSaving, hasUnsavedChanges, onSave]);

  if (!documentPath) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyInner}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 className={styles.emptyTitle}>从左侧挑一份文稿</h3>
          <p className={styles.emptyDescription}>设定、大纲、正文和附录都收在同一张写作纸面里，先选中文稿再开始进入正文。</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.editor}>
      <header className={styles.editorHeader}>
        <div className={styles.documentInfo}>
          <p className={styles.documentPath}>{documentPath}</p>
          <h2 className={styles.documentTitle}>{documentNode?.label ?? "未命名文档"}</h2>
        </div>
        <div className={styles.editorActions}>
          <div className={styles.viewModeToggle}>
            {(["edit", "split", "preview"] as const).map((mode) => (
              <button
                key={mode}
                className={styles.viewModeBtn}
                data-active={viewMode === mode ? "true" : "false"}
                onClick={() => setViewMode(mode)}
                type="button"
              >
                {mode === "edit" ? "编辑" : mode === "split" ? "分栏" : "预览"}
              </button>
            ))}
          </div>
          <Button
            type="secondary"
            shape="round"
            size="small"
            loading={isSaving}
            disabled={!hasUnsavedChanges}
            onClick={onSave}
          >
            {isSaving ? "保存中…" : hasUnsavedChanges ? "提醒保存" : "未改动"}
          </Button>
        </div>
      </header>
      <div className={styles.editorBody} data-mode={viewMode}>
        {viewMode !== "preview" ? (
          <div className={styles.editPane}>
            <textarea
              ref={textareaRef}
              className={styles.textarea}
              value={content}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="开始整理你的设定、章节或正文…"
              spellCheck={false}
            />
          </div>
        ) : null}
        {viewMode !== "edit" ? (
          <div className={styles.previewPane}>
            <MarkdownPreview content={content} />
          </div>
        ) : null}
      </div>
      <footer aria-live="polite" className={styles.editorFooter}>
        <span className={styles.stats}>{content.length} 字符 · {content.split(/\s+/).filter(Boolean).length} 词</span>
        <span className={hasUnsavedChanges ? styles.unsavedIndicator : styles.savedIndicator}>
          {hasUnsavedChanges ? "本地未保存" : "已就绪"}
        </span>
      </footer>
    </div>
  );
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
      return `<pre class="${styles.codeBlock}" data-lang="${lang}"><code>${code.trim()}</code></pre>`;
    });

    return html;
  };

  return (
    <div
      className={styles.preview}
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}
