"use client";

import { useState } from "react";
import { Dropdown, Menu } from "@arco-design/web-react";

import {
  hasSelectedDescendant,
  resolveInitialNodeExpandedState,
  resolveNodeExpandedState,
} from "@/features/studio/components/tree/document-tree-support";
import type { DocumentTreeNode } from "@/features/studio/components/page/studio-page-support";

type DocumentTreeProps = {
  selectedPath: string | null;
  selectedPathSignal: symbol;
  tree: DocumentTreeNode[];
  onSelectNode: (node: DocumentTreeNode) => void;
  onAddDocument?: (parentPath: string) => void;
  onAddFolder?: (parentPath: string) => void;
  onRenameNode?: (node: DocumentTreeNode) => void;
  onDeleteNode?: (node: DocumentTreeNode) => void;
  onCollapse?: () => void;
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
  onCollapse,
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

  return (
    <nav aria-label="作品目录" className="dt-root">
      {/* 顶部装饰 */}
      <div className="dt-root__glow" />

      {/* 头部 */}
      <div className="dt-header">
        {rootCreateMenu ? (
          <Dropdown trigger="contextMenu" droplist={rootCreateMenu} position="bl">
            <div className="dt-header__content">
              <h2 className="dt-header__title">创作结构</h2>
              <span className="dt-header__count">{tree.length} 卷</span>
            </div>
          </Dropdown>
        ) : (
          <div className="dt-header__content">
            <h2 className="dt-header__title">创作结构</h2>
            <span className="dt-header__count">{tree.length} 卷</span>
          </div>
        )}
        {onCollapse ? (
          <button
            className="dt-header__collapse-btn"
            onClick={onCollapse}
            title="收起目录"
            type="button"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        ) : null}
      </div>

      {/* 树列表 */}
      <ul className="dt-list">
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
      className={`dt-node ${isSelected ? "dt-node--selected" : ""} ${isFolder ? "dt-node--folder" : ""}`}
      style={{ paddingLeft: `${14 + depth * 18}px` }}
      type="button"
      onClick={handleClick}
    >
      {isFolder ? (
        <span className={`dt-node__chevron ${isExpanded ? "dt-node__chevron--open" : ""}`}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </span>
      ) : (
        <span className="dt-node__icon">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </span>
      )}
      <span className="dt-node__label">{node.label}</span>
      {node.icon === "stale" ? (
        <span className="dt-node__stale" title="需要更新" />
      ) : null}
    </button>
  );

  const treeRow = <div className="dt-row">{treeButton}</div>;

  return (
    <li className="dt-item">
      {hasContextMenu ? (
        <Dropdown trigger="contextMenu" droplist={contextMenu} position="bl">
          {treeRow}
        </Dropdown>
      ) : treeRow}
      {isFolder && isExpanded && hasChildren ? (
        <ul className="dt-list dt-list--nested">
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
