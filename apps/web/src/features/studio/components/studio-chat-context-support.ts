import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

export function countStudioContextFiles(nodes: readonly DocumentTreeNode[]): number {
  return nodes.reduce((count, node) => count + countStudioContextFilesForNode(node), 0);
}

export function buildStudioContextFileCountMap(nodes: readonly DocumentTreeNode[]) {
  const fileCountByPath = new Map<string, number>();
  nodes.forEach((node) => {
    collectStudioContextFileCount(node, fileCountByPath);
  });
  return fileCountByPath;
}

export function countStudioContextFilesForNode(node: Readonly<DocumentTreeNode>): number {
  if (node.type === "file") {
    return 1;
  }
  return countStudioContextFiles(node.children ?? []);
}

export function filterStudioContextTree(
  nodes: readonly DocumentTreeNode[],
  query: string,
): DocumentTreeNode[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return [...nodes];
  }
  return nodes.flatMap((node) => filterStudioContextNode(node, normalizedQuery));
}

function filterStudioContextNode(
  node: Readonly<DocumentTreeNode>,
  normalizedQuery: string,
): DocumentTreeNode[] {
  if (matchesStudioContextNode(node, normalizedQuery)) {
    return [{ ...node }];
  }
  if (node.type === "file") {
    return [];
  }
  const filteredChildren = filterStudioContextTree(node.children ?? [], normalizedQuery);
  if (filteredChildren.length === 0) {
    return [];
  }
  return [{
    ...node,
    children: filteredChildren,
  }];
}

function matchesStudioContextNode(
  node: Readonly<Pick<DocumentTreeNode, "label" | "path">>,
  normalizedQuery: string,
) {
  return node.label.toLowerCase().includes(normalizedQuery)
    || node.path.toLowerCase().includes(normalizedQuery);
}

function collectStudioContextFileCount(
  node: Readonly<DocumentTreeNode>,
  fileCountByPath: Map<string, number>,
) {
  const count = node.type === "file"
    ? 1
    : (node.children ?? []).reduce(
      (sum, child) => sum + collectStudioContextFileCount(child, fileCountByPath),
      0,
    );
  fileCountByPath.set(node.path, count);
  return count;
}
