import assert from "node:assert/strict";
import test from "node:test";

import {
  buildJsonRelationGraphOption,
  DEFAULT_JSON_RELATION_GRAPH_THEME,
  resolveJsonRelationGraphTheme,
  type JsonRelationGraphTheme,
} from "@/features/studio/components/document/json-relation-graph-support";
import type { JsonRelationGraphModel } from "@/features/studio/components/document/json-document-support";

test("resolveJsonRelationGraphTheme reads CSS variables and falls back to defaults", () => {
  const theme = resolveJsonRelationGraphTheme({
    getPropertyValue(propertyName: string) {
      const values: Record<string, string> = {
        "--accent-success": "#4f8f66",
        "--accent-success-soft": "rgba(79, 143, 102, 0.12)",
        "--text-primary": "#2a241f",
      };
      return values[propertyName] ?? "";
    },
  });

  assert.equal(theme.categories.character.accent, "#4f8f66");
  assert.equal(theme.categories.character.fill, "rgba(79, 143, 102, 0.12)");
  assert.equal(
    theme.categories.faction.stroke,
    DEFAULT_JSON_RELATION_GRAPH_THEME.categories.faction.stroke,
  );
  assert.equal(theme.textPrimary, "#2a241f");
  assert.equal(theme.textSecondary, DEFAULT_JSON_RELATION_GRAPH_THEME.textSecondary);
});

test("buildJsonRelationGraphOption uses resolved theme colors instead of raw CSS variable strings", () => {
  const graph: JsonRelationGraphModel = {
    nodes: [
      {
        category: "character",
        id: "char_001",
        label: "林渊",
        raw: {},
      },
      {
        category: "faction",
        id: "fac_001",
        label: "青岚宗",
        raw: {},
      },
    ],
    edges: [
      {
        category: "membership",
        id: "mem_001",
        label: "核心弟子",
        raw: {},
        source: "char_001",
        target: "fac_001",
      },
    ],
  };
  const theme: JsonRelationGraphTheme = {
    ...DEFAULT_JSON_RELATION_GRAPH_THEME,
    categories: {
      ...DEFAULT_JSON_RELATION_GRAPH_THEME.categories,
      character: {
        accent: "#5c8f73",
        fill: "rgba(92, 143, 115, 0.14)",
        stroke: "#5c8f73",
      },
    },
    edges: {
      ...DEFAULT_JSON_RELATION_GRAPH_THEME.edges,
      membership: "#5c8f73",
    },
    textPrimary: "#312a24",
    textSecondary: "#746b60",
  };

  const option = buildJsonRelationGraphOption(graph, null, theme);
  const series = (Array.isArray(option.series) ? option.series[0] : null) as {
    data?: Array<{ itemStyle: { borderColor: string; color: string } }>;
    label?: { color: string };
    links?: Array<{ lineStyle: { color: string } }>;
  } | null;
  assert.ok(series && !Array.isArray(series));

  const node = Array.isArray(series.data) ? series.data[0] : null;
  const edge = Array.isArray(series.links) ? series.links[0] : null;
  const label = series.label;
  const tooltip = option.tooltip as { textStyle: { color: string } };

  assert.equal(node?.itemStyle.color, "rgba(92, 143, 115, 0.14)");
  assert.equal(node?.itemStyle.borderColor, "#5c8f73");
  assert.equal(edge?.lineStyle.color, "#5c8f73");
  assert.ok(label);
  assert.equal(label.color, "#312a24");
  assert.equal(tooltip.textStyle.color, "#312a24");
});
