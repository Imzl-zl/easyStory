import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioJsonPreviewState,
  listStudioJsonPreviewSourcePaths,
  resolveStudioJsonPreviewMode,
} from "./json-document-support";

test("resolveStudioJsonPreviewMode routes chinese data-layer graph files to graph preview", () => {
  assert.equal(resolveStudioJsonPreviewMode("数据层/人物.json"), "graph");
  assert.equal(resolveStudioJsonPreviewMode("数据层/势力关系.json"), "graph");
  assert.equal(resolveStudioJsonPreviewMode("数据层/事件.json"), "raw");
  assert.equal(resolveStudioJsonPreviewMode("数据层/结构定义.json"), "raw");
  assert.equal(resolveStudioJsonPreviewMode("导出/前端数据.json"), "raw");
  assert.equal(resolveStudioJsonPreviewMode("设定/人物.md"), null);
});

test("listStudioJsonPreviewSourcePaths keeps only existing graph sources plus current file", () => {
  assert.deepEqual(
    listStudioJsonPreviewSourcePaths("数据层/人物关系.json", [
      "数据层/人物.json",
      "数据层/人物关系.json",
    ]),
    ["数据层/人物.json", "数据层/人物关系.json"],
  );
  assert.deepEqual(
    listStudioJsonPreviewSourcePaths("导出/前端数据.json", ["导出/前端数据.json"]),
    ["导出/前端数据.json"],
  );
});

test("buildStudioJsonPreviewState formats raw json files", () => {
  const preview = buildStudioJsonPreviewState("导出/前端数据.json", {
    "导出/前端数据.json": "{\"version\":2,\"ready\":true}",
  });
  assert.deepEqual(preview, {
    formattedContent: "{\n  \"version\": 2,\n  \"ready\": true\n}",
    kind: "raw",
    status: "ready",
    value: {
      ready: true,
      version: 2,
    },
  });
});

test("buildStudioJsonPreviewState builds a relation graph from split data-layer sources", () => {
  const preview = buildStudioJsonPreviewState("数据层/人物关系.json", {
    "数据层/人物.json": JSON.stringify({
      characters: [{ id: "char_001", name: "萧炎", status: "alive" }],
    }),
    "数据层/势力.json": JSON.stringify({
      factions: [{ id: "fac_001", name: "天府联盟", status: "active" }],
    }),
    "数据层/人物关系.json": JSON.stringify({
      character_relations: [{ source: "char_001", target: "char_002", type: "宿敌" }],
    }),
    "数据层/势力关系.json": JSON.stringify({
      faction_relations: [{ source: "fac_001", target: "fac_002", type: "对抗" }],
    }),
    "数据层/隶属关系.json": JSON.stringify({
      memberships: [{ character_id: "char_001", faction_id: "fac_001", role: "盟主" }],
    }),
  });

  assert.equal(preview?.kind, "graph");
  assert.equal(preview?.status, "error");
  if (!preview || preview.kind !== "graph" || preview.status !== "error") {
    assert.fail("expected graph preview error");
  }
  assert.match(preview.issues[0]?.message ?? "", /不存在的节点/);
});

test("buildStudioJsonPreviewState builds a ready graph when split sources are complete", () => {
  const preview = buildStudioJsonPreviewState("数据层/势力关系.json", {
    "数据层/人物.json": JSON.stringify({
      characters: [
        { id: "char_001", name: "萧炎", status: "alive" },
        { id: "char_002", name: "魂天帝", status: "alive" },
      ],
    }),
    "数据层/势力.json": JSON.stringify({
      factions: [
        { id: "fac_001", name: "天府联盟", status: "active" },
        { id: "fac_002", name: "魂殿", status: "active" },
      ],
    }),
    "数据层/人物关系.json": JSON.stringify({
      character_relations: [{ source: "char_001", target: "char_002", type: "宿敌" }],
    }),
    "数据层/势力关系.json": JSON.stringify({
      faction_relations: [{ source: "fac_001", target: "fac_002", type: "对抗" }],
    }),
    "数据层/隶属关系.json": JSON.stringify({
      memberships: [{ character_id: "char_001", faction_id: "fac_001", role: "盟主" }],
    }),
  });

  assert.equal(preview?.kind, "graph");
  assert.equal(preview?.status, "ready");
  if (!preview || preview.kind !== "graph" || preview.status !== "ready") {
    assert.fail("expected ready graph preview");
  }
  assert.equal(preview.activeSourceLabel, "势力关系");
  assert.equal(preview.graph.nodes.length, 4);
  assert.equal(preview.graph.edges.length, 3);
  assert.deepEqual(preview.sourceSummary, {
    characterCount: 2,
    characterRelationCount: 1,
    factionCount: 2,
    factionRelationCount: 1,
    membershipCount: 1,
  });
});

test("buildStudioJsonPreviewState keeps empty split relation files in an explicit empty state", () => {
  const preview = buildStudioJsonPreviewState("数据层/势力关系.json", {
    "数据层/人物.json": JSON.stringify({
      characters: [{ id: "char_001", name: "王云飞" }],
    }),
    "数据层/势力.json": JSON.stringify({
      factions: [{ id: "fac_001", name: "市刑侦支队" }],
    }),
    "数据层/人物关系.json": JSON.stringify({
      character_relations: [{ source: "char_001", target: "char_002", type: "搭档" }],
    }),
    "数据层/势力关系.json": JSON.stringify({ faction_relations: [] }),
    "数据层/隶属关系.json": JSON.stringify({
      memberships: [{ character_id: "char_001", faction_id: "fac_001", role: "刑警" }],
    }),
  });

  assert.equal(preview?.kind, "graph");
  assert.equal(preview?.status, "empty");
  if (!preview || preview.kind !== "graph" || preview.status !== "empty") {
    assert.fail("expected graph empty state");
  }
  assert.equal(preview.activeSourceLabel, "势力关系");
  assert.match(preview.message, /势力关系文件还是空的/);
});

test("buildStudioJsonPreviewState rejects bare arrays for graph source files", () => {
  const preview = buildStudioJsonPreviewState("数据层/人物.json", {
    "数据层/人物.json": '[{"id":"char_001","name":"王云飞"}]',
  });

  assert.equal(preview?.kind, "graph");
  assert.equal(preview?.status, "error");
  if (!preview || preview.kind !== "graph" || preview.status !== "error") {
    assert.fail("expected graph preview error");
  }
  assert.match(preview.issues[0]?.message ?? "", /包含 "characters" 数组的对象/);
});
