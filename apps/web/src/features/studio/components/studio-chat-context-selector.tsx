"use client";

import { useCallback, useMemo, useState } from "react";
import type { CSSProperties, RefObject } from "react";
import { Checkbox } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

import {
  buildStudioContextFileCountMap,
  countStudioContextFiles,
  filterStudioContextTree,
} from "./studio-chat-context-support";

const CONTEXT_PICKER_PANEL_CLASS =
  "overflow-hidden rounded-xl border border-[rgba(44,36,22,0.1)] bg-white/95 shadow-[0_18px_46px_rgba(44,36,22,0.16)] backdrop-blur-sm";

type StudioChatContextSelectorContentProps = {
  availableContexts: DocumentTreeNode[];
  onToggleContext: (path: string) => void;
  panelRef: RefObject<HTMLDivElement | null>;
  panelStyle: CSSProperties | undefined;
  selectedContextPaths: string[];
};

export function StudioChatContextSelectorContent({
  availableContexts,
  onToggleContext,
  panelRef,
  panelStyle,
  selectedContextPaths,
}: Readonly<StudioChatContextSelectorContentProps>) {
  const [contextSearchQuery, setContextSearchQuery] = useState("");
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({});

  const { filteredContexts, filteredFileCountByPath } = useMemo(() => {
    const nextFilteredContexts = filterStudioContextTree(availableContexts, contextSearchQuery);
    return {
      filteredContexts: nextFilteredContexts,
      filteredFileCountByPath: buildStudioContextFileCountMap(nextFilteredContexts),
    };
  },
    [availableContexts, contextSearchQuery],
  );
  const totalFileCount = useMemo(
    () => countStudioContextFiles(availableContexts),
    [availableContexts],
  );
  const isSearching = contextSearchQuery.trim().length > 0;

  const toggleFolder = useCallback((path: string, isExpanded: boolean) => {
    setExpandedPaths((current) => ({
      ...current,
      [path]: !isExpanded,
    }));
  }, []);

  return (
    <div
      className={CONTEXT_PICKER_PANEL_CLASS}
      ref={panelRef}
      style={panelStyle}
    >
      <p className="border-b border-[rgba(44,36,22,0.06)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)]">
        附加文档上下文 ({selectedContextPaths.length}/{totalFileCount})
      </p>
      <input
        type="text"
        className="w-full border-b border-[rgba(44,36,22,0.06)] bg-transparent px-3 py-2 text-sm focus:bg-[rgba(107,143,113,0.05)] focus:outline-none"
        placeholder="搜索文稿..."
        value={contextSearchQuery}
        onChange={(event) => setContextSearchQuery(event.target.value)}
      />
      <div className="max-h-52 overflow-y-auto scrollbar-thin py-1">
        {filteredContexts.length > 0 ? (
          filteredContexts.map((node) => (
            <StudioChatContextTreeNode
              depth={0}
              expandedPaths={expandedPaths}
              fileCountByPath={filteredFileCountByPath}
              isSearching={isSearching}
              key={node.id}
              node={node}
              selectedContextPaths={selectedContextPaths}
              onToggleContext={onToggleContext}
              onToggleFolder={toggleFolder}
            />
          ))
        ) : (
          <p className="px-3 py-3 text-sm text-[var(--text-muted)]">没有找到匹配的文稿。</p>
        )}
      </div>
    </div>
  );
}

type StudioChatContextTreeNodeProps = {
  depth: number;
  expandedPaths: Record<string, boolean>;
  fileCountByPath: ReadonlyMap<string, number>;
  isSearching: boolean;
  node: DocumentTreeNode;
  onToggleContext: (path: string) => void;
  onToggleFolder: (path: string, isExpanded: boolean) => void;
  selectedContextPaths: string[];
};

function StudioChatContextTreeNode({
  depth,
  expandedPaths,
  fileCountByPath,
  isSearching,
  node,
  onToggleContext,
  onToggleFolder,
  selectedContextPaths,
}: Readonly<StudioChatContextTreeNodeProps>) {
  const rowPaddingStyle = {
    paddingLeft: `${12 + depth * 14}px`,
  } satisfies CSSProperties;

  if (node.type === "file") {
    return (
      <label
        className="flex cursor-pointer items-center gap-2 py-1 pr-3 hover:bg-[rgba(107,143,113,0.05)]"
        style={rowPaddingStyle}
      >
        <Checkbox
          checked={selectedContextPaths.includes(node.path)}
          onChange={() => onToggleContext(node.path)}
        />
        <span className="min-w-0 flex-1 truncate text-sm text-[var(--text-primary)]">
          {node.label}
        </span>
      </label>
    );
  }

  const visibleFileCount = fileCountByPath.get(node.path) ?? 0;
  const hasSelectedDescendant = selectedContextPaths.some((path) => path.startsWith(`${node.path}/`));
  const isExpanded = isSearching
    || expandedPaths[node.path]
    || (!(node.path in expandedPaths) && (depth === 0 || hasSelectedDescendant));

  return (
    <div>
      <button
        className={`flex w-full items-center gap-2 py-1.5 pr-3 text-left text-xs font-medium text-[var(--text-secondary)] hover:bg-[rgba(107,143,113,0.05)] ${isExpanded ? "bg-[rgba(107,143,113,0.08)]" : ""}`}
        style={rowPaddingStyle}
        type="button"
        onClick={() => onToggleFolder(node.path, isExpanded)}
      >
        <span className={`transition-transform ${isExpanded ? "rotate-90" : ""}`}>▶</span>
        <span className="min-w-0 flex-1 truncate">{node.label}</span>
        <span className="opacity-60">{visibleFileCount}</span>
      </button>
      {isExpanded
        ? node.children?.map((child) => (
          <StudioChatContextTreeNode
            depth={depth + 1}
            expandedPaths={expandedPaths}
            fileCountByPath={fileCountByPath}
            isSearching={isSearching}
            key={child.id}
            node={child}
            selectedContextPaths={selectedContextPaths}
            onToggleContext={onToggleContext}
            onToggleFolder={onToggleFolder}
          />
        ))
        : null}
    </div>
  );
}
