"use client";

import type { EChartsOption } from "echarts";

import type {
  JsonRelationGraphEdge,
  JsonRelationGraphModel,
  JsonRelationGraphNode,
} from "@/features/studio/components/document/json-document-support";

const CATEGORY_META = {
  character: {
    badge: "人物",
  },
  faction: {
    badge: "势力",
  },
} as const;

const EDGE_META = {
  character_relation: {
    badge: "人物关系",
    dash: "dashed" as const,
  },
  faction_relation: {
    badge: "势力关系",
    dash: "dashed" as const,
  },
  membership: {
    badge: "隶属",
    dash: "solid" as const,
  },
} as const;

type CssVariableReader = {
  getPropertyValue: (propertyName: string) => string;
};

export type JsonRelationGraphTheme = {
  categories: {
    character: {
      accent: string;
      fill: string;
      stroke: string;
    };
    faction: {
      accent: string;
      fill: string;
      stroke: string;
    };
  };
  edges: {
    character_relation: string;
    faction_relation: string;
    membership: string;
  };
  textPrimary: string;
  textSecondary: string;
};

export const DEFAULT_JSON_RELATION_GRAPH_THEME: JsonRelationGraphTheme = {
  categories: {
    character: {
      accent: "#6b8f71",
      fill: "rgba(107, 143, 113, 0.10)",
      stroke: "#6b8f71",
    },
    faction: {
      accent: "#b8944a",
      fill: "rgba(184, 148, 74, 0.10)",
      stroke: "#b8944a",
    },
  },
  edges: {
    character_relation: "#b8944a",
    faction_relation: "#9a7eb8",
    membership: "#6b8f71",
  },
  textPrimary: "#3d3832",
  textSecondary: "#7e776d",
};

export type JsonRelationGraphSelection =
  | { id: string; kind: "edge" }
  | { id: string; kind: "node" }
  | null;

export type JsonRelationGraphInspector = {
  accentColor: string;
  badges: string[];
  facts: Array<{ label: string; value: string }>;
  kindLabel: string;
  rawContent: string;
  rawTitle: string;
  subtitle: string;
  title: string;
};

export function buildJsonRelationGraphOption(
  graph: JsonRelationGraphModel,
  selection: JsonRelationGraphSelection,
  theme: JsonRelationGraphTheme = DEFAULT_JSON_RELATION_GRAPH_THEME,
): EChartsOption {
  return {
    animationDuration: 260,
    animationEasing: "cubicOut",
    backgroundColor: "transparent",
    tooltip: {
      backgroundColor: "rgba(255,253,249,0.96)",
      borderColor: "rgba(101,92,82,0.14)",
      borderWidth: 1,
      className: "studio-json-graph-tooltip",
      formatter: (params: unknown) => {
        if (!isTooltipParams(params)) {
          return "";
        }
        return formatTooltip(params.dataType, params.data, theme.textSecondary);
      },
      textStyle: {
        color: theme.textPrimary,
        fontFamily: "inherit",
      },
    },
    series: [{
      data: graph.nodes.map((node) => buildNodeOption(node, graph.edges, selection, theme)),
      draggable: false,
      edgeLabel: {
        formatter: "{c}",
        show: false,
      },
      emphasis: {
        focus: "adjacency",
      },
      force: {
        edgeLength: [120, 200],
        gravity: 0.08,
        repulsion: 420,
      },
      label: {
        color: theme.textPrimary,
        fontSize: 12,
        overflow: "truncate",
        position: "right",
        show: true,
        width: 110,
      },
      layout: "force",
      links: graph.edges.map((edge) => buildEdgeOption(edge, selection, theme)),
      roam: true,
      selectedMode: false,
      symbolKeepAspect: true,
      type: "graph",
    }],
  } as EChartsOption;
}

export function resolveJsonRelationGraphTheme(
  styleSource: CssVariableReader | null | undefined,
): JsonRelationGraphTheme {
  return {
    categories: {
      character: {
        accent: readCssVariable(styleSource, "--accent-success", DEFAULT_JSON_RELATION_GRAPH_THEME.categories.character.accent),
        fill: readCssVariable(styleSource, "--accent-success-soft", DEFAULT_JSON_RELATION_GRAPH_THEME.categories.character.fill),
        stroke: readCssVariable(styleSource, "--accent-success", DEFAULT_JSON_RELATION_GRAPH_THEME.categories.character.stroke),
      },
      faction: {
        accent: readCssVariable(styleSource, "--accent-warning", DEFAULT_JSON_RELATION_GRAPH_THEME.categories.faction.accent),
        fill: readCssVariable(styleSource, "--accent-warning-soft", DEFAULT_JSON_RELATION_GRAPH_THEME.categories.faction.fill),
        stroke: readCssVariable(styleSource, "--accent-warning", DEFAULT_JSON_RELATION_GRAPH_THEME.categories.faction.stroke),
      },
    },
    edges: {
      character_relation: readCssVariable(styleSource, "--accent-warning", DEFAULT_JSON_RELATION_GRAPH_THEME.edges.character_relation),
      faction_relation: readCssVariable(styleSource, "--accent-purple", DEFAULT_JSON_RELATION_GRAPH_THEME.edges.faction_relation),
      membership: readCssVariable(styleSource, "--accent-success", DEFAULT_JSON_RELATION_GRAPH_THEME.edges.membership),
    },
    textPrimary: readCssVariable(styleSource, "--text-primary", DEFAULT_JSON_RELATION_GRAPH_THEME.textPrimary),
    textSecondary: readCssVariable(styleSource, "--text-secondary", DEFAULT_JSON_RELATION_GRAPH_THEME.textSecondary),
  };
}

export function isValidJsonRelationGraphSelection(
  graph: JsonRelationGraphModel,
  selection: JsonRelationGraphSelection,
) {
  if (!selection) {
    return true;
  }
  return selection.kind === "node"
    ? graph.nodes.some((node) => node.id === selection.id)
    : graph.edges.some((edge) => edge.id === selection.id);
}

export function resolveJsonRelationGraphInspector(
  graph: JsonRelationGraphModel,
  selection: JsonRelationGraphSelection,
  theme: JsonRelationGraphTheme = DEFAULT_JSON_RELATION_GRAPH_THEME,
): JsonRelationGraphInspector | null {
  if (!selection) {
    return null;
  }
  if (selection.kind === "node") {
    return buildNodeInspector(graph, selection.id, theme);
  }
  return buildEdgeInspector(graph, selection.id, theme);
}

function buildNodeOption(
  node: JsonRelationGraphNode,
  edges: JsonRelationGraphEdge[],
  selection: JsonRelationGraphSelection,
  theme: JsonRelationGraphTheme,
) {
  const meta = theme.categories[node.category];
  const selected = selection?.kind === "node" && selection.id === node.id;
  const dimmed = selection ? !isNodeConnectedToSelection(node.id, edges, selection) : false;
  return {
    category: node.category,
    id: node.id,
    itemStyle: {
      borderColor: meta.stroke,
      borderWidth: selected ? 3 : 1.5,
      color: meta.fill,
      opacity: dimmed ? 0.35 : 1,
      shadowBlur: selected ? 16 : 8,
      shadowColor: selected ? "rgba(58,45,29,0.18)" : "rgba(58,45,29,0.08)",
    },
    label: {
      opacity: dimmed ? 0.45 : 1,
    },
    name: node.label,
    raw: node.raw,
    symbol: node.category === "character" ? "circle" : "roundRect",
    symbolSize: selected ? 76 : node.category === "character" ? 58 : 66,
    value: CATEGORY_META[node.category].badge,
  };
}

function buildEdgeOption(
  edge: JsonRelationGraphEdge,
  selection: JsonRelationGraphSelection,
  theme: JsonRelationGraphTheme,
) {
  const meta = EDGE_META[edge.category];
  const selected = selection?.kind === "edge" && selection.id === edge.id;
  const dimmed = selection ? !isEdgeConnectedToSelection(edge, selection) : false;
  return {
    id: edge.id,
    label: edge.label,
    lineStyle: {
      color: theme.edges[edge.category],
      opacity: dimmed ? 0.18 : 0.72,
      type: meta.dash,
      width: selected ? 3.4 : edge.category === "membership" ? 2.4 : 2,
    },
    raw: edge.raw,
    source: edge.source,
    target: edge.target,
    value: edge.label,
  };
}

function buildNodeInspector(
  graph: JsonRelationGraphModel,
  nodeId: string,
  theme: JsonRelationGraphTheme,
) {
  const node = graph.nodes.find((item) => item.id === nodeId);
  if (!node) {
    return null;
  }
  const connectedEdges = graph.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
  return {
    accentColor: theme.categories[node.category].accent,
    badges: [
      CATEGORY_META[node.category].badge,
      `${connectedEdges.length} 条关联`,
    ],
    facts: [
      { label: "节点 ID", value: node.id },
      { label: "节点类型", value: CATEGORY_META[node.category].badge },
      { label: "关联边", value: connectedEdges.map((edge) => edge.label).join(" / ") || "暂无" },
    ],
    kindLabel: CATEGORY_META[node.category].badge,
    rawContent: JSON.stringify(node.raw, null, 2),
    rawTitle: `${CATEGORY_META[node.category].badge}原始字段`,
    subtitle: "当前选中的人物 / 势力节点",
    title: node.label,
  };
}

function buildEdgeInspector(
  graph: JsonRelationGraphModel,
  edgeId: string,
  theme: JsonRelationGraphTheme,
) {
  const edge = graph.edges.find((item) => item.id === edgeId);
  if (!edge) {
    return null;
  }
  const source = graph.nodes.find((node) => node.id === edge.source);
  const target = graph.nodes.find((node) => node.id === edge.target);
  return {
    accentColor: theme.edges[edge.category],
    badges: [
      EDGE_META[edge.category].badge,
      `${source?.label ?? edge.source} → ${target?.label ?? edge.target}`,
    ],
    facts: [
      { label: "连线 ID", value: edge.id },
      { label: "连线类型", value: EDGE_META[edge.category].badge },
      { label: "起点", value: source?.label ?? edge.source },
      { label: "终点", value: target?.label ?? edge.target },
    ],
    kindLabel: EDGE_META[edge.category].badge,
    rawContent: JSON.stringify(edge.raw, null, 2),
    rawTitle: `${EDGE_META[edge.category].badge}原始字段`,
    subtitle: "当前选中的关系 / 隶属连线",
    title: edge.label,
  };
}

function isNodeConnectedToSelection(
  nodeId: string,
  edges: JsonRelationGraphEdge[],
  selection: NonNullable<JsonRelationGraphSelection>,
) {
  if (selection.kind === "node") {
    return selection.id === nodeId || edges.some((edge) =>
      (edge.source === selection.id && edge.target === nodeId)
      || (edge.target === selection.id && edge.source === nodeId));
  }
  return edges.some((edge) => edge.id === selection.id && (edge.source === nodeId || edge.target === nodeId));
}

function isEdgeConnectedToSelection(
  edge: JsonRelationGraphEdge,
  selection: NonNullable<JsonRelationGraphSelection>,
) {
  if (selection.kind === "edge") {
    return selection.id === edge.id;
  }
  return edge.source === selection.id || edge.target === selection.id;
}

function formatTooltip(
  dataType: string,
  data: unknown,
  textSecondary: string,
) {
  if (!isTooltipRecord(data)) {
    return "";
  }
  if (dataType === "node") {
    return [
      `<div style="font-weight:600;margin-bottom:4px;">${escapeHtml(String(data.name ?? ""))}</div>`,
      `<div style="font-size:12px;color:${textSecondary};">${escapeHtml(String(data.value ?? ""))}</div>`,
    ].join("");
  }
  return [
    `<div style="font-weight:600;margin-bottom:4px;">${escapeHtml(String(data.value ?? ""))}</div>`,
    `<div style="font-size:12px;color:${textSecondary};">${escapeHtml(String(data.source ?? ""))} → ${escapeHtml(String(data.target ?? ""))}</div>`,
  ].join("");
}

function readCssVariable(
  styleSource: CssVariableReader | null | undefined,
  propertyName: string,
  fallback: string,
) {
  const value = styleSource?.getPropertyValue(propertyName).trim();
  return value || fallback;
}

function isTooltipRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isTooltipParams(
  value: unknown,
): value is { data: unknown; dataType: string } {
  return isTooltipRecord(value)
    && typeof value.dataType === "string"
    && "data" in value;
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}
