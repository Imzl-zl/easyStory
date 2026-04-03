import type { ChapterSummary, ProjectDocumentTreeNode } from "@/lib/api/types";

export type StudioPanelKey = "setting" | "outline" | "opening-plan" | "chapter";
export type StudioChapterListState = "loading" | "error" | "empty" | "ready";
export type StudioDocumentEntryKind = "file" | "folder";
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

const STUDIO_PANEL_OPTIONS: Array<{
  key: StudioPanelKey;
  label: string;
}> = [
  { key: "setting", label: "设定" },
  { key: "outline", label: "大纲" },
  { key: "opening-plan", label: "开篇设计" },
  { key: "chapter", label: "章节" },
];

const PANEL_DEFAULT_DOCUMENT_PATHS: Record<
  Exclude<StudioPanelKey, "chapter">,
  string
> = {
  setting: "设定/世界观.md",
  outline: "大纲/总大纲.md",
  "opening-plan": "大纲/开篇设计.md",
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

export function buildStudioPathWithParams(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
): string {
  const next = new URLSearchParams(currentSearch);
  Object.entries(patches).forEach(([key, value]) => {
    if (value === null) {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  const search = next.toString();
  return search ? `${pathname}?${search}` : pathname;
}

export function listStudioPanelOptions() {
  return STUDIO_PANEL_OPTIONS;
}

export function getStudioPanelLabel(panel: StudioPanelKey) {
  return STUDIO_PANEL_OPTIONS.find((item) => item.key === panel)?.label ?? "设定";
}

export function resolveStudioChapterListState({
  chapters,
  errorMessage,
  isLoading,
}: {
  chapters: ChapterSummary[] | undefined;
  errorMessage: string | null;
  isLoading: boolean;
}): StudioChapterListState {
  if (isLoading && !chapters) {
    return "loading";
  }
  if (errorMessage && (!chapters || chapters.length === 0)) {
    return "error";
  }
  if (!chapters || chapters.length === 0) {
    return "empty";
  }
  return "ready";
}

export function resolveSelectedChapterNumber(
  chapters: ChapterSummary[] | undefined,
  rawChapter: string | null,
) {
  if (rawChapter) {
    const parsed = Number(rawChapter);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  const firstStale = chapters?.find((chapter) => chapter.status === "stale");
  return firstStale?.chapter_number ?? chapters?.[0]?.chapter_number ?? null;
}

export function listStaleChapters(chapters: ChapterSummary[] | undefined) {
  return chapters?.filter((chapter) => chapter.status === "stale") ?? [];
}

export function resolveStudioPanel(value: string | null): StudioPanelKey {
  return STUDIO_PANEL_OPTIONS.some((item) => item.key === value)
    ? (value as StudioPanelKey)
    : "setting";
}

export function resolveDefaultDocumentPathFromPanel(
  panelValue: string | null,
  chapters: ChapterSummary[] | undefined,
  rawChapter: string | null,
) {
  const panel = STUDIO_PANEL_OPTIONS.find((item) => item.key === panelValue)?.key;
  if (!panel) {
    return null;
  }
  if (panel === "chapter") {
    const chapterNumber = resolveSelectedChapterNumber(chapters, rawChapter);
    return chapterNumber === null
      ? null
      : `正文/第${String(chapterNumber).padStart(3, "0")}章.md`;
  }
  return PANEL_DEFAULT_DOCUMENT_PATHS[panel];
}

export function resolveDocumentPathFromNode(node: DocumentTreeNode): string {
  return node.path;
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

export function resolveStudioDocumentPath(
  rawDocumentPath: string | null,
  tree: DocumentTreeNode[],
  treeReady: boolean,
  fallbackDocumentPath: string | null,
) {
  if (!rawDocumentPath) {
    return fallbackDocumentPath;
  }
  if (!treeReady) {
    return null;
  }
  return findNodeByPath(tree, rawDocumentPath)?.path ?? fallbackDocumentPath;
}

export function findClosestRemainingFilePath(
  tree: DocumentTreeNode[],
  removedPath: string,
  currentPath: string | null,
) {
  const filePaths = listDocumentTreeFilePaths(tree);
  const remainingPaths = filePaths.filter((path) => !isDocumentTreePathAffected(path, removedPath));
  if (remainingPaths.length === 0) {
    return null;
  }
  if (!currentPath) {
    return remainingPaths[0] ?? null;
  }
  const currentIndex = filePaths.findIndex((path) => path === currentPath);
  if (currentIndex === -1) {
    return remainingPaths[0] ?? null;
  }
  for (let index = currentIndex + 1; index < filePaths.length; index += 1) {
    const candidatePath = filePaths[index];
    if (candidatePath && !isDocumentTreePathAffected(candidatePath, removedPath)) {
      return candidatePath;
    }
  }
  for (let index = currentIndex - 1; index >= 0; index -= 1) {
    const candidatePath = filePaths[index];
    if (candidatePath && !isDocumentTreePathAffected(candidatePath, removedPath)) {
      return candidatePath;
    }
  }
  return remainingPaths[0] ?? null;
}

export function isDocumentTreePathAffected(path: string, targetPath: string) {
  return path === targetPath || path.startsWith(`${targetPath}/`);
}

export function remapDocumentTreePath(
  path: string,
  previousPath: string,
  nextPath: string | null,
): string | null {
  if (!isDocumentTreePathAffected(path, previousPath)) {
    return path;
  }
  if (nextPath === null) {
    return null;
  }
  if (path === previousPath) {
    return nextPath;
  }
  return `${nextPath}${path.slice(previousPath.length)}`;
}

export function buildStudioDocumentEntryPath(
  parentPath: string,
  rawName: string,
  kind: StudioDocumentEntryKind,
): string | null {
  const normalizedName = normalizeStudioDocumentEntryName(parentPath, rawName, kind);
  if (!normalizedName) {
    return null;
  }
  return parentPath ? `${parentPath}/${normalizedName}` : normalizedName;
}

export function normalizeStudioDocumentEntryName(
  parentPath: string,
  rawName: string,
  kind: StudioDocumentEntryKind,
): string | null {
  const trimmed = rawName.trim();
  if (!trimmed || trimmed === "." || trimmed === "..") {
    return null;
  }
  if (trimmed.includes("/") || trimmed.includes("\\")) {
    return null;
  }
  if (kind === "file" && isContentDocumentParentPath(parentPath)) {
    return normalizeStudioChapterEntryName(trimmed);
  }
  if (kind === "folder") {
    return hasSupportedStudioDocumentSuffix(trimmed) ? null : trimmed;
  }
  if (isDataLayerDocumentParentPath(parentPath)) {
    return hasSupportedStudioDocumentSuffix(trimmed) ? trimmed : `${trimmed}.json`;
  }
  return hasSupportedStudioDocumentSuffix(trimmed) ? trimmed : `${trimmed}.md`;
}

export function readStudioDocumentEntryBaseName(node: DocumentTreeNode) {
  const leafName = node.path.split("/").at(-1) ?? "";
  return node.type === "file" ? leafName.replace(/\.(json|md)$/i, "") : leafName;
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

function isDataLayerDocumentParentPath(parentPath: string) {
  return parentPath === DATA_ROOT_PATH || parentPath.startsWith(`${DATA_ROOT_PATH}/`);
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

function hasSupportedStudioDocumentSuffix(value: string) {
  return /\.(json|md)$/i.test(value);
}

export function listDocumentTreeFilePaths(tree: DocumentTreeNode[]): string[] {
  return tree.flatMap((node) => {
    if (node.type === "file") {
      return [node.path];
    }
    return node.children ? listDocumentTreeFilePaths(node.children) : [];
  });
}

function containsDatabaseNode(nodes: DocumentTreeNode[]): boolean {
  return nodes.some((node) => node.origin === "database" || containsDatabaseNode(node.children ?? []));
}

function isContentDocumentParentPath(parentPath: string) {
  return parentPath === CONTENT_ROOT_PATH || parentPath.startsWith(`${CONTENT_ROOT_PATH}/`);
}

function normalizeStudioChapterEntryName(rawName: string) {
  const chapterName = rawName.replace(/\.md$/i, "");
  const matched = chapterName.match(/^(?:第)?\s*(\d{1,3})\s*章?$/);
  if (!matched) {
    return null;
  }
  const chapterNumber = Number(matched[1]);
  if (!Number.isInteger(chapterNumber) || chapterNumber <= 0) {
    return null;
  }
  return `第${String(chapterNumber).padStart(3, "0")}章.md`;
}

function parseChapterNumberFromDocumentPath(documentPath: string) {
  const matched = documentPath.match(CHAPTER_DOCUMENT_PATH);
  return matched ? Number(matched[1]) : null;
}

function readCanonicalChapterPath(chapterNumber: number) {
  return `正文/第${String(chapterNumber).padStart(3, "0")}章.md`;
}
