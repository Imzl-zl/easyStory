"use client";

const DATA_CHARACTERS_PATH = "数据层/人物.json";
const DATA_FACTIONS_PATH = "数据层/势力.json";
const DATA_CHARACTER_RELATIONS_PATH = "数据层/人物关系.json";
const DATA_FACTION_RELATIONS_PATH = "数据层/势力关系.json";
const DATA_MEMBERSHIPS_PATH = "数据层/隶属关系.json";

const DATA_LAYER_GRAPH_SOURCE_PATHS = [
  DATA_CHARACTERS_PATH,
  DATA_FACTIONS_PATH,
  DATA_CHARACTER_RELATIONS_PATH,
  DATA_FACTION_RELATIONS_PATH,
  DATA_MEMBERSHIPS_PATH,
] as const;

const DATA_LAYER_GRAPH_SOURCE_PATH_SET = new Set<string>(DATA_LAYER_GRAPH_SOURCE_PATHS);
const DATA_LAYER_GRAPH_SOURCE_META = {
  [DATA_CHARACTERS_PATH]: {
    collectionKey: "characters",
    emptyMessage: "当前人物文件还是空的，先补人物节点，关系图才会出现人物网络。",
    label: "人物",
  },
  [DATA_FACTIONS_PATH]: {
    collectionKey: "factions",
    emptyMessage: "当前势力文件还是空的，补上势力节点后才能看见阵营结构。",
    label: "势力",
  },
  [DATA_CHARACTER_RELATIONS_PATH]: {
    collectionKey: "character_relations",
    emptyMessage: "当前人物关系文件还是空的，补上人物之间的关系后才会出现人物连线。",
    label: "人物关系",
  },
  [DATA_FACTION_RELATIONS_PATH]: {
    collectionKey: "faction_relations",
    emptyMessage: "当前势力关系文件还是空的，补上势力之间的关系后才会出现阵营连线。",
    label: "势力关系",
  },
  [DATA_MEMBERSHIPS_PATH]: {
    collectionKey: "memberships",
    emptyMessage: "当前隶属文件还是空的，补上人物和势力的归属关系后才会出现归队连线。",
    label: "隶属",
  },
} as const;

type JsonRecord = Record<string, unknown>;

type ParsedJsonDocument =
  | { status: "empty" }
  | { issue: JsonPreviewIssue; status: "error" }
  | { status: "ready"; value: unknown };

export type JsonPreviewIssue = {
  message: string;
  path: string;
};

export type JsonRelationGraphNode = {
  category: "character" | "faction";
  id: string;
  label: string;
  raw: JsonRecord;
};

export type JsonRelationGraphEdge = {
  category: "character_relation" | "faction_relation" | "membership";
  id: string;
  label: string;
  raw: JsonRecord;
  source: string;
  target: string;
};

export type JsonRelationGraphModel = {
  edges: JsonRelationGraphEdge[];
  nodes: JsonRelationGraphNode[];
};

export type JsonGraphSourceSummary = {
  characterCount: number;
  characterRelationCount: number;
  factionCount: number;
  factionRelationCount: number;
  membershipCount: number;
};

export type StudioJsonPreviewState =
  | { activeSourceLabel: string; kind: "graph"; message: string; sourceSummary: JsonGraphSourceSummary; status: "empty" }
  | { activeSourceLabel: string; issues: JsonPreviewIssue[]; kind: "graph"; sourceSummary: JsonGraphSourceSummary; status: "error" }
  | { activeSourceLabel: string; graph: JsonRelationGraphModel; kind: "graph"; sourceSummary: JsonGraphSourceSummary; status: "ready" }
  | { kind: "raw"; message: string; status: "empty" }
  | { issues: JsonPreviewIssue[]; kind: "raw"; status: "error" }
  | { formattedContent: string; kind: "raw"; status: "ready"; value: unknown };

export function isJsonDocumentPath(documentPath: string | null) {
  return Boolean(documentPath?.toLowerCase().endsWith(".json"));
}

export function resolveStudioJsonPreviewMode(documentPath: string | null): "graph" | "raw" | null {
  if (!documentPath || !isJsonDocumentPath(documentPath)) {
    return null;
  }
  return DATA_LAYER_GRAPH_SOURCE_PATH_SET.has(documentPath) ? "graph" : "raw";
}

export function listStudioJsonPreviewSourcePaths(
  documentPath: string | null,
  availablePaths: readonly string[] = [],
) {
  const mode = resolveStudioJsonPreviewMode(documentPath);
  if (!documentPath || !mode) {
    return [];
  }
  if (mode === "raw") {
    return [documentPath];
  }
  const availablePathSet = new Set(availablePaths);
  return DATA_LAYER_GRAPH_SOURCE_PATHS.filter(
    (path) => path === documentPath || availablePathSet.size === 0 || availablePathSet.has(path),
  );
}

export function buildStudioJsonPreviewState(
  documentPath: string | null,
  sourceContents: Readonly<Record<string, string>>,
): StudioJsonPreviewState | null {
  const mode = resolveStudioJsonPreviewMode(documentPath);
  if (!documentPath || !mode) {
    return null;
  }
  if (mode === "raw") {
    return buildRawJsonPreviewState(documentPath, sourceContents[documentPath] ?? "");
  }
  return buildGraphJsonPreviewState(documentPath, sourceContents);
}

function buildRawJsonPreviewState(documentPath: string, content: string): StudioJsonPreviewState {
  const parsed = parseJsonDocument(documentPath, content);
  if (parsed.status === "empty") {
    return {
      kind: "raw",
      message: "当前 JSON 文件还是空的，保存结构化内容后这里会显示格式化预览。",
      status: "empty",
    };
  }
  if (parsed.status === "error") {
    return { issues: [parsed.issue], kind: "raw", status: "error" };
  }
  return {
    formattedContent: JSON.stringify(parsed.value, null, 2),
    kind: "raw",
    status: "ready",
    value: parsed.value,
  };
}

function buildGraphJsonPreviewState(
  documentPath: string,
  sourceContents: Readonly<Record<string, string>>,
): StudioJsonPreviewState {
  const activeSourceMeta = DATA_LAYER_GRAPH_SOURCE_META[documentPath as keyof typeof DATA_LAYER_GRAPH_SOURCE_META];
  const issues: JsonPreviewIssue[] = [];
  const characters = readNamedRecordArray(
    DATA_CHARACTERS_PATH,
    parseJsonDocument(DATA_CHARACTERS_PATH, sourceContents[DATA_CHARACTERS_PATH] ?? ""),
    "characters",
    issues,
  );
  const factions = readNamedRecordArray(
    DATA_FACTIONS_PATH,
    parseJsonDocument(DATA_FACTIONS_PATH, sourceContents[DATA_FACTIONS_PATH] ?? ""),
    "factions",
    issues,
  );
  const characterRelations = readNamedRecordArray(
    DATA_CHARACTER_RELATIONS_PATH,
    parseJsonDocument(DATA_CHARACTER_RELATIONS_PATH, sourceContents[DATA_CHARACTER_RELATIONS_PATH] ?? ""),
    "character_relations",
    issues,
  );
  const factionRelations = readNamedRecordArray(
    DATA_FACTION_RELATIONS_PATH,
    parseJsonDocument(DATA_FACTION_RELATIONS_PATH, sourceContents[DATA_FACTION_RELATIONS_PATH] ?? ""),
    "faction_relations",
    issues,
  );
  const memberships = readNamedRecordArray(
    DATA_MEMBERSHIPS_PATH,
    parseJsonDocument(DATA_MEMBERSHIPS_PATH, sourceContents[DATA_MEMBERSHIPS_PATH] ?? ""),
    "memberships",
    issues,
  );
  const sourceSummary = {
    characterCount: characters.length,
    characterRelationCount: characterRelations.length,
    factionCount: factions.length,
    factionRelationCount: factionRelations.length,
    membershipCount: memberships.length,
  };
  if (issues.length > 0) {
    return { activeSourceLabel: activeSourceMeta.label, issues, kind: "graph", sourceSummary, status: "error" };
  }
  const activeSourceCount = readActiveSourceCount(documentPath, {
    characters,
    characterRelations,
    factions,
    factionRelations,
    memberships,
  });
  if (activeSourceCount === 0) {
    return {
      activeSourceLabel: activeSourceMeta.label,
      kind: "graph",
      message: activeSourceMeta.emptyMessage,
      sourceSummary,
      status: "empty",
    };
  }

  const nodes = [
    ...buildGraphNodes(DATA_CHARACTERS_PATH, "character", characters, issues),
    ...buildGraphNodes(DATA_FACTIONS_PATH, "faction", factions, issues),
  ];
  validateUniqueNodeIds(nodes, issues);
  const edges = [
    ...buildRelationEdges(characterRelations, DATA_CHARACTER_RELATIONS_PATH, "character_relation", "人物关系", issues),
    ...buildRelationEdges(factionRelations, DATA_FACTION_RELATIONS_PATH, "faction_relation", "势力关系", issues),
    ...buildMembershipEdges(memberships, DATA_MEMBERSHIPS_PATH, issues),
  ];
  validateEdgeTargets(nodes, edges, issues);
  if (issues.length > 0) {
    return { activeSourceLabel: activeSourceMeta.label, issues, kind: "graph", sourceSummary, status: "error" };
  }
  if (nodes.length === 0 && edges.length === 0) {
    return {
      activeSourceLabel: activeSourceMeta.label,
      kind: "graph",
      message: "数据层还没有可渲染的人物、势力或关系。",
      sourceSummary,
      status: "empty",
    };
  }
  return {
    activeSourceLabel: activeSourceMeta.label,
    graph: {
      edges,
      nodes,
    },
    kind: "graph",
    sourceSummary,
    status: "ready",
  };
}

function readActiveSourceCount(
  documentPath: string,
  collections: Readonly<{
    characters: JsonRecord[];
    characterRelations: JsonRecord[];
    factions: JsonRecord[];
    factionRelations: JsonRecord[];
    memberships: JsonRecord[];
  }>,
) {
  if (documentPath === DATA_CHARACTERS_PATH) {
    return collections.characters.length;
  }
  if (documentPath === DATA_FACTIONS_PATH) {
    return collections.factions.length;
  }
  if (documentPath === DATA_CHARACTER_RELATIONS_PATH) {
    return collections.characterRelations.length;
  }
  if (documentPath === DATA_FACTION_RELATIONS_PATH) {
    return collections.factionRelations.length;
  }
  return collections.memberships.length;
}

function parseJsonDocument(path: string, content: string): ParsedJsonDocument {
  const trimmed = content.trim();
  if (!trimmed) {
    return { status: "empty" };
  }
  try {
    return { status: "ready", value: JSON.parse(trimmed) };
  } catch (error) {
    return {
      issue: {
        message: `不是有效 JSON：${readErrorMessage(error)}`,
        path,
      },
      status: "error",
    };
  }
}

function readNamedRecordArray(
  path: string,
  parsed: ParsedJsonDocument,
  collectionKey: string,
  issues: JsonPreviewIssue[],
) {
  if (parsed.status === "empty") {
    return [];
  }
  if (parsed.status === "error") {
    issues.push(parsed.issue);
    return [];
  }
  const candidate = isJsonRecord(parsed.value) ? parsed.value[collectionKey] : null;
  if (!Array.isArray(candidate)) {
    issues.push({
      message: `需要是包含 "${collectionKey}" 数组的对象。`,
      path,
    });
    return [];
  }
  if (!candidate.every(isJsonRecord)) {
    issues.push({
      message: "数组里的每一项都必须是对象。",
      path,
    });
    return [];
  }
  return candidate;
}

function buildGraphNodes(
  path: string,
  category: JsonRelationGraphNode["category"],
  records: JsonRecord[],
  issues: JsonPreviewIssue[],
) {
  return records.flatMap((record, index) => {
    const id = readRequiredString(record, "id", path, index, issues);
    const label = readRequiredString(record, "name", path, index, issues);
    if (!id || !label) {
      return [];
    }
    return [{ category, id, label, raw: record }];
  });
}

function validateUniqueNodeIds(nodes: JsonRelationGraphNode[], issues: JsonPreviewIssue[]) {
  const seenIds = new Set<string>();
  nodes.forEach((node) => {
    if (seenIds.has(node.id)) {
      issues.push({
        message: `节点 ID "${node.id}" 重复，图谱里每个人物或势力都必须有唯一 ID。`,
        path: node.category === "character" ? DATA_CHARACTERS_PATH : DATA_FACTIONS_PATH,
      });
      return;
    }
    seenIds.add(node.id);
  });
}

function buildRelationEdges(
  records: JsonRecord[],
  path: string,
  category: JsonRelationGraphEdge["category"],
  fallbackLabel: string,
  issues: JsonPreviewIssue[],
) {
  return records.flatMap((record, index) => {
    const source = readRequiredString(record, "source", path, index, issues);
    const target = readRequiredString(record, "target", path, index, issues);
    if (!source || !target) {
      return [];
    }
    return [{
      category,
      id: readOptionalString(record, "id") ?? `relation:${index}:${source}:${target}`,
      label: readOptionalString(record, "type") ?? readOptionalString(record, "label") ?? fallbackLabel,
      raw: record,
      source,
      target,
    }];
  });
}

function buildMembershipEdges(records: JsonRecord[], path: string, issues: JsonPreviewIssue[]) {
  return records.flatMap((record, index) => {
    const source = readRequiredString(record, "character_id", path, index, issues);
    const target = readRequiredString(record, "faction_id", path, index, issues);
    if (!source || !target) {
      return [];
    }
    return [{
      category: "membership" as const,
      id: readOptionalString(record, "id") ?? `membership:${index}:${source}:${target}`,
      label: readOptionalString(record, "role") ?? "隶属",
      raw: record,
      source,
      target,
    }];
  });
}

function validateEdgeTargets(
  nodes: JsonRelationGraphNode[],
  edges: JsonRelationGraphEdge[],
  issues: JsonPreviewIssue[],
) {
  const nodeIds = new Set(nodes.map((node) => node.id));
  edges.forEach((edge) => {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      issues.push({
        message: `连线 "${edge.label}" 指向了不存在的节点：${edge.source} -> ${edge.target}。`,
        path: resolveEdgePath(edge.category),
      });
    }
  });
}

function resolveEdgePath(category: JsonRelationGraphEdge["category"]) {
  if (category === "character_relation") {
    return DATA_CHARACTER_RELATIONS_PATH;
  }
  if (category === "faction_relation") {
    return DATA_FACTION_RELATIONS_PATH;
  }
  return DATA_MEMBERSHIPS_PATH;
}

function readRequiredString(
  record: JsonRecord,
  key: string,
  path: string,
  index: number,
  issues: JsonPreviewIssue[],
) {
  const value = readOptionalString(record, key);
  if (value) {
    return value;
  }
  issues.push({
    message: `第 ${index + 1} 项缺少必填字符串字段 "${key}"。`,
    path,
  });
  return null;
}

function readOptionalString(record: JsonRecord, key: string) {
  const value = record[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "未知解析错误";
}
