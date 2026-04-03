"use client";

import { useState } from "react";
import { Dropdown, Menu } from "@arco-design/web-react";

import {
  hasSelectedDescendant,
  resolveInitialNodeExpandedState,
  resolveNodeExpandedState,
} from "@/features/studio/components/document-tree-support";
import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

type DocumentTreeProps = {
  selectedPath: string | null;
  selectedPathSignal: symbol;
  tree: DocumentTreeNode[];
  onSelectNode: (node: DocumentTreeNode) => void;
  onAddDocument?: (parentPath: string) => void;
  onAddFolder?: (parentPath: string) => void;
  onRenameNode?: (node: DocumentTreeNode) => void;
  onDeleteNode?: (node: DocumentTreeNode) => void;
};

export function DocumentTree({
  selectedPath,
  selectedPathSignal,
  tree,
  onSelectNode,
  onAddDocument,
  onAddFolder,
  onRenameNode,
  onDeleteNode,
}: Readonly<DocumentTreeProps>) {
  const rootCreateTargets = tree.filter((node) => node.type === "folder" && node.canCreateChild);
  const rootCreateMenu = rootCreateTargets.length > 0 && (onAddDocument || onAddFolder) ? (
    <Menu>
      {(onAddDocument || onAddFolder) ? (
        <Menu.SubMenu key="__root__" title="根目录">
          {onAddDocument ? (
            <Menu.Item key="__root__-file" onClick={() => onAddDocument("")}>
              新建文档
            </Menu.Item>
          ) : null}
          {onAddFolder ? (
            <Menu.Item key="__root__-folder" onClick={() => onAddFolder("")}>
              新建文件夹
            </Menu.Item>
          ) : null}
        </Menu.SubMenu>
      ) : null}
      {rootCreateTargets.map((node) => (
        <Menu.SubMenu key={node.path} title={node.label}>
          {onAddDocument ? (
            <Menu.Item key={`${node.path}-file`} onClick={() => onAddDocument(node.path)}>
              新建文档
            </Menu.Item>
          ) : null}
          {onAddFolder ? (
            <Menu.Item key={`${node.path}-folder`} onClick={() => onAddFolder(node.path)}>
              新建文件夹
            </Menu.Item>
          ) : null}
        </Menu.SubMenu>
      ))}
    </Menu>
  ) : null;
  const header = (
    <div className="flex items-start justify-between gap-3">
      <div className="flex min-w-0 flex-col gap-1.5">
        <h2 className="m-0 font-serif text-[1.45rem] font-bold tracking-tight text-[var(--text-primary)]">创作结构</h2>
        <p className="m-0 text-xs leading-relaxed text-[var(--text-muted)]">右键标题区或节点可管理</p>
      </div>
    </div>
  );

  return (
    <nav aria-label="作品目录" className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-gradient-to-b from-[#fefdfb] to-[#f9f7f3]">
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none [background-image:url('data:image/svg+xml,%3Csvg_viewBox%3D%220%200%20400%20400%22_xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter_id%3D%22n%22%3E%3CfeTurbulence_type%3D%22fractalNoise%22_baseFrequency%3D%221.2%22_numOctaves%3D%223%22_stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect_width%3D%22100%25%22_height%3D%22100%25%22_filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')]" />
      <div className="absolute top-0 left-0 right-0 h-[150px] bg-gradient-to-b from-white/50 to-transparent pointer-events-none" />

      <div className="relative z-10 px-4 pt-6 pb-4">
        {rootCreateMenu ? (
          <Dropdown trigger="contextMenu" droplist={rootCreateMenu} position="bl">
            {header}
          </Dropdown>
        ) : (
          header
        )}
      </div>

      <ul className="relative z-10 flex-1 min-h-0 overflow-y-auto px-2.5 pb-4 scrollbar-thin [&::-webkit-scrollbar]:w-[4px] [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-[2px] [&::-webkit-scrollbar-thumb]:bg-[rgba(44,36,22,0.12)]">
        {tree.map((node) => (
          <DocumentTreeNodeItem
            key={node.id}
            node={node}
            selectedPath={selectedPath}
            selectedPathSignal={selectedPathSignal}
            onSelectNode={onSelectNode}
            onAddDocument={onAddDocument}
            onAddFolder={onAddFolder}
            onRenameNode={onRenameNode}
            onDeleteNode={onDeleteNode}
            depth={0}
          />
        ))}
      </ul>
    </nav>
  );
}

type DocumentTreeNodeItemProps = {
  node: DocumentTreeNode;
  selectedPath: string | null;
  selectedPathSignal: symbol;
  onSelectNode: (node: DocumentTreeNode) => void;
  onAddDocument?: (parentPath: string) => void;
  onAddFolder?: (parentPath: string) => void;
  onRenameNode?: (node: DocumentTreeNode) => void;
  onDeleteNode?: (node: DocumentTreeNode) => void;
  depth: number;
};

function DocumentTreeNodeItem({
  node,
  selectedPath,
  selectedPathSignal,
  onSelectNode,
  onAddDocument,
  onAddFolder,
  onRenameNode,
  onDeleteNode,
  depth,
}: Readonly<DocumentTreeNodeItemProps>) {
  const isFolder = node.type === "folder";
  const [manualExpanded, setManualExpanded] = useState(() =>
    isFolder
      ? resolveInitialNodeExpandedState({
          depth,
          nodePath: node.path,
          selectedPath,
        })
      : false,
  );
  const [collapsedSelectionSignal, setCollapsedSelectionSignal] = useState<symbol | null>(null);
  const isSelected = selectedPath === node.path;
  const hasChildren = node.children && node.children.length > 0;
  const isSelectedDescendant = isFolder ? hasSelectedDescendant(node.path, selectedPath) : false;
  const isExpanded = isFolder
    ? resolveNodeExpandedState({
        collapsedSelectionSignal,
        manualExpanded,
        nodePath: node.path,
        selectedPath,
        selectedPathSignal,
      })
    : false;

  const handleClick = () => {
    if (isFolder) {
      if (isExpanded) {
        setManualExpanded(false);
        setCollapsedSelectionSignal(isSelectedDescendant ? selectedPathSignal : null);
        return;
      }
      setManualExpanded(true);
      setCollapsedSelectionSignal(null);
    } else {
      onSelectNode(node);
    }
  };

  const contextMenu = buildNodeActionMenu({
    isFolder,
    node,
    onAddDocument,
    onAddFolder,
    onDeleteNode,
    onRenameNode,
  });
  const hasContextMenu = contextMenu !== null;

  const treeButton = (
    <button
      aria-expanded={isFolder ? isExpanded : undefined}
      className={`flex min-w-0 flex-1 items-center gap-2 py-2 px-2.5 border-none rounded-lg bg-transparent text-[var(--text-primary)] text-sm font-medium text-left cursor-pointer transition-all ${isSelected ? "bg-gradient-to-br from-[rgba(107,143,113,0.12)] to-[rgba(107,143,113,0.06)] shadow-[inset_0_0_0_1px_rgba(107,143,113,0.15)] hover:bg-gradient-to-br hover:from-[rgba(107,143,113,0.18)] hover:to-[rgba(107,143,113,0.1)]" : "hover:bg-[rgba(107,143,113,0.08)] hover:translate-x-[3px]"}`}
      style={{ paddingLeft: `${12 + depth * 16}px` }}
      type="button"
      onClick={handleClick}
    >
      {isFolder ? (
        <span className={`flex items-center justify-center w-[18px] h-[18px] text-[var(--accent-primary)] text-[0.7rem] transition-transform ${isExpanded ? "rotate-90" : ""}`}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </span>
      ) : (
        <span className="flex items-center justify-center w-[18px] h-[18px] text-[#c4a76c] text-[0.85rem]">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </span>
      )}
      <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap tracking-tight">{node.label}</span>
      {node.icon === "stale" ? (
        <span className="inline-flex h-2.5 w-2.5 ml-auto rounded-full bg-[#c4a76c] shadow-[0_0_0_3px_rgba(196,167,108,0.14)]" title="需要更新" />
      ) : null}
    </button>
  );
  const treeRow = <div className="group flex items-center gap-1">{treeButton}</div>;

  return (
    <li className="mb-0.5">
      {hasContextMenu ? (
        <Dropdown
          trigger="contextMenu"
          droplist={contextMenu}
          position="bl"
        >
          {treeRow}
        </Dropdown>
      ) : treeRow}
      {isFolder && isExpanded && hasChildren ? (
        <ul className="overflow-y-auto px-3 pb-5 scrollbar-thin">
          {node.children!.map((child) => (
            <DocumentTreeNodeItem
              key={child.id}
              node={child}
              selectedPath={selectedPath}
              selectedPathSignal={selectedPathSignal}
              onSelectNode={onSelectNode}
              onAddDocument={onAddDocument}
              onAddFolder={onAddFolder}
              onRenameNode={onRenameNode}
              onDeleteNode={onDeleteNode}
              depth={depth + 1}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function buildNodeActionMenu({
  isFolder,
  node,
  onAddDocument,
  onAddFolder,
  onDeleteNode,
  onRenameNode,
}: {
  isFolder: boolean;
  node: DocumentTreeNode;
  onAddDocument?: (parentPath: string) => void;
  onAddFolder?: (parentPath: string) => void;
  onDeleteNode?: (node: DocumentTreeNode) => void;
  onRenameNode?: (node: DocumentTreeNode) => void;
}) {
  const createMenu = buildNodeCreateMenu({
    isFolder,
    node,
    onAddDocument,
    onAddFolder,
  });
  if (!createMenu && !node.canRename && !node.canDelete) {
    return null;
  }
  return (
    <Menu>
      {createMenu?.props.children}
      {node.canRename && onRenameNode ? (
        <Menu.Item key="rename" onClick={() => onRenameNode(node)}>
          重命名
        </Menu.Item>
      ) : null}
      {node.canDelete && onDeleteNode ? (
        <Menu.Item key="delete" onClick={() => onDeleteNode(node)}>
          删除
        </Menu.Item>
      ) : null}
    </Menu>
  );
}

function buildNodeCreateMenu({
  isFolder,
  node,
  onAddDocument,
  onAddFolder,
}: {
  isFolder: boolean;
  node: DocumentTreeNode;
  onAddDocument?: (parentPath: string) => void;
  onAddFolder?: (parentPath: string) => void;
}) {
  if (!isFolder || !node.canCreateChild || (!onAddDocument && !onAddFolder)) {
    return null;
  }
  return (
    <Menu>
      {onAddDocument ? (
        <Menu.Item key="add-document" onClick={() => onAddDocument(node.path)}>
          新建文档
        </Menu.Item>
      ) : null}
      {onAddFolder ? (
        <Menu.Item key="add-folder" onClick={() => onAddFolder(node.path)}>
          新建文件夹
        </Menu.Item>
      ) : null}
    </Menu>
  );
}
