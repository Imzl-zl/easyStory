import type { ChapterSummary, ProjectDocumentTreeNode } from "@/lib/api/types";

export type DocumentTreeNodeOrigin = "custom" | "database" | "fixed";

export type DocumentTreeNode = {
  canCreateChild?: boolean;
  canDelete?: boolean;
  canRename?: boolean;
  children?: DocumentTreeNode[];
  icon?: string;
  id: string;
  label: string;
  origin: DocumentTreeNodeOrigin;
  path: string;
  type: "folder" | "file";
};

const SETTINGS_ROOT_PATH = "设定";
const OUTLINE_ROOT_PATH = "大纲";
const CONTENT_ROOT_PATH = "正文";
const DATA_ROOT_PATH = "数据层";
const CHAPTER_DOCUMENT_PATH = /^正文(?:\/[^/]+)*\/第(\d{3})章\.md$/;

const ROOT_DISPLAY_ORDER = [
  "项目说明.md",
  SETTINGS_ROOT_PATH,
  DATA_ROOT_PATH,
  OUTLINE_ROOT_PATH,
  CONTENT_ROOT_PATH,
  "时间轴",
  "附录",
  "校验",
  "导出",
] as const;

const CANONICAL_DATABASE_PATHS = new Set([
  "大纲/总大纲.md",
  "大纲/开篇设计.md",
]);

export const CONTENT_ROOT_PATH_EXPORT = CONTENT_ROOT_PATH;
export const DATA_ROOT_PATH_EXPORT = DATA_ROOT_PATH;

export function buildStudioDocumentTree(
  chapters: ChapterSummary[],
  customTreeNodes: ProjectDocumentTreeNode[] | undefined,
): DocumentTreeNode[] {
  const customRoots = new Map((customTreeNodes ?? []).map((node) => [node.path, node]));
  const chaptersByNumber = new Map(chapters.map((chapter) => [chapter.chapter_number, chapter]));
  const orderedTree: DocumentTreeNode[] = [];

  ROOT_DISPLAY_ORDER.forEach((path) => {
    if (path === SETTINGS_ROOT_PATH) {
      orderedTree.push(
        buildFixedRootNode({
          children: mapCustomTreeNodes(customRoots.get(SETTINGS_ROOT_PATH)?.children ?? []),
          label: SETTINGS_ROOT_PATH,
          path: SETTINGS_ROOT_PATH,
        }),
      );
      customRoots.delete(SETTINGS_ROOT_PATH);
      return;
    }
    if (path === OUTLINE_ROOT_PATH) {
      orderedTree.push(
        buildFixedRootNode({
          children: [
            createDatabaseFileNode("大纲/总大纲.md"),
            createDatabaseFileNode("大纲/开篇设计.md"),
            ...mapCustomTreeNodes(customRoots.get(OUTLINE_ROOT_PATH)?.children ?? []),
          ],
          label: OUTLINE_ROOT_PATH,
          path: OUTLINE_ROOT_PATH,
        }),
      );
      customRoots.delete(OUTLINE_ROOT_PATH);
      return;
    }
    if (path === CONTENT_ROOT_PATH) {
      orderedTree.push(
        buildFixedRootNode({
          children: buildContentRootChildren(
            chaptersByNumber,
            customRoots.get(CONTENT_ROOT_PATH)?.children ?? [],
          ),
          label: CONTENT_ROOT_PATH,
          path: CONTENT_ROOT_PATH,
        }),
      );
      customRoots.delete(CONTENT_ROOT_PATH);
      return;
    }
    const customRoot = customRoots.get(path);
    if (!customRoot) {
      return;
    }
    orderedTree.push(mapCustomTreeNode(customRoot));
    customRoots.delete(path);
  });

  customRoots.forEach((node) => {
    orderedTree.push(mapCustomTreeNode(node));
  });
  return orderedTree;
}

export function findNodeByPath(tree: DocumentTreeNode[], path: string): DocumentTreeNode | null {
  for (const node of tree) {
    if (node.path === path) {
      return node;
    }
    if (node.children) {
      const found = findNodeByPath(node.children, path);
      if (found) {
        return found;
      }
    }
  }
  return null;
}

export function findFirstFilePath(tree: DocumentTreeNode[]): string | null {
  return listDocumentTreeFilePaths(tree)[0] ?? null;
}

export function listDocumentTreeFilePaths(tree: DocumentTreeNode[]): string[] {
  return tree.flatMap((node) => {
    if (node.type === "file") {
      return [node.path];
    }
    return node.children ? listDocumentTreeFilePaths(node.children) : [];
  });
}

export function isContentDocumentParentPath(parentPath: string) {
  return parentPath === CONTENT_ROOT_PATH || parentPath.startsWith(`${CONTENT_ROOT_PATH}/`);
}

export function isDataLayerDocumentParentPath(parentPath: string) {
  return parentPath === DATA_ROOT_PATH || parentPath.startsWith(`${DATA_ROOT_PATH}/`);
}

export function hasSupportedStudioDocumentSuffix(value: string) {
  return /\.(json|md)$/i.test(value);
}

export function parseChapterNumberFromDocumentPath(documentPath: string) {
  const matched = documentPath.match(CHAPTER_DOCUMENT_PATH);
  return matched ? Number(matched[1]) : null;
}

function buildFixedRootNode({
  canCreateChild = true,
  children,
  label,
  path,
}: {
  canCreateChild?: boolean;
  children: DocumentTreeNode[];
  label: string;
  path: string;
}): DocumentTreeNode {
  return {
    canCreateChild,
    children,
    id: `fixed-folder-${path}`,
    label,
    origin: "fixed",
    path,
    type: "folder",
  };
}

function createDatabaseFileNode(path: string): DocumentTreeNode {
  return {
    id: `database-file-${path}`,
    label: readLeafName(path),
    origin: "database",
    path,
    type: "file",
  };
}

function createDatabaseChapterNode(chapter: ChapterSummary, path = readCanonicalChapterPath(chapter.chapter_number)): DocumentTreeNode {
  return {
    icon: chapter.status === "stale" ? "stale" : undefined,
    id: `database-file-${path}`,
    label: readLeafName(path),
    origin: "database",
    path,
    type: "file",
  };
}

function buildContentRootChildren(
  chaptersByNumber: Map<number, ChapterSummary>,
  customNodes: ProjectDocumentTreeNode[],
) {
  const mappedCustomNodes = mapContentTreeNodes(customNodes, chaptersByNumber);
  const remainingChapterNodes = Array.from(chaptersByNumber.values())
    .sort((left, right) => left.chapter_number - right.chapter_number)
    .map((chapter) => createDatabaseChapterNode(chapter));
  return [...mappedCustomNodes, ...remainingChapterNodes];
}

function mapContentTreeNodes(
  nodes: ProjectDocumentTreeNode[],
  chaptersByNumber: Map<number, ChapterSummary>,
): DocumentTreeNode[] {
  return nodes
    .map((node) => mapContentTreeNode(node, chaptersByNumber))
    .filter((node): node is DocumentTreeNode => node !== null);
}

function mapContentTreeNode(
  node: ProjectDocumentTreeNode,
  chaptersByNumber: Map<number, ChapterSummary>,
): DocumentTreeNode | null {
  if (node.node_type === "file") {
    const chapterNumber = parseChapterNumberFromDocumentPath(node.path);
    if (chapterNumber === null) {
      return null;
    }
    const chapter = chaptersByNumber.get(chapterNumber);
    chaptersByNumber.delete(chapterNumber);
    return createDatabaseChapterNode(
      chapter ?? ({ chapter_number: chapterNumber, status: "draft" } as ChapterSummary),
      node.path,
    );
  }
  const children = mapContentTreeNodes(node.children, chaptersByNumber);
  return {
    canCreateChild: true,
    canDelete: containsDatabaseNode(children) ? false : true,
    canRename: true,
    children,
    id: `custom-folder-${node.path}`,
    label: node.label,
    origin: "custom",
    path: node.path,
    type: "folder",
  };
}

function mapCustomTreeNodes(nodes: ProjectDocumentTreeNode[]): DocumentTreeNode[] {
  return nodes
    .filter((node) => !CANONICAL_DATABASE_PATHS.has(node.path))
    .map((node) => mapCustomTreeNode(node));
}

function mapCustomTreeNode(node: ProjectDocumentTreeNode): DocumentTreeNode {
  return {
    canCreateChild: node.node_type === "folder" ? true : undefined,
    canDelete: true,
    canRename: true,
    children: node.node_type === "folder" ? mapCustomTreeNodes(node.children) : undefined,
    id: `custom-${node.node_type}-${node.path}`,
    label: node.label,
    origin: "custom",
    path: node.path,
    type: node.node_type,
  };
}

function readLeafName(path: string) {
  return path.split("/").at(-1) ?? path;
}

function containsDatabaseNode(nodes: DocumentTreeNode[]): boolean {
  return nodes.some((node) => node.origin === "database" || containsDatabaseNode(node.children ?? []));
}

function readCanonicalChapterPath(chapterNumber: number) {
  return `正文/第${String(chapterNumber).padStart(3, "0")}章.md`;
}
