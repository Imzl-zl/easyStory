import assert from "node:assert/strict";
import test from "node:test";

import type { AgentConfigSummary, SkillConfigSummary } from "@/lib/api/types";

import {
  buildConfigRegistryPathWithParams,
  parseConfigRegistryDocument,
  resolveActiveConfigId,
  resolveConfigRegistryRoutePatches,
  resolveConfigRegistryType,
} from "./config-registry-support";

test("resolveConfigRegistryType falls back to skills for invalid values", () => {
  assert.equal(resolveConfigRegistryType("hooks"), "hooks");
  assert.equal(resolveConfigRegistryType("mcp_servers"), "mcp_servers");
  assert.equal(resolveConfigRegistryType("unknown"), "skills");
  assert.equal(resolveConfigRegistryType(null), "skills");
});

test("buildConfigRegistryPathWithParams updates and removes query params", () => {
  assert.equal(
    buildConfigRegistryPathWithParams("/workspace/lobby/config-registry", "type=skills&item=s1", {
      item: "s2",
      type: "agents",
    }),
    "/workspace/lobby/config-registry?type=agents&item=s2",
  );
  assert.equal(
    buildConfigRegistryPathWithParams("/workspace/lobby/config-registry", "type=skills&item=s1", {
      item: null,
    }),
    "/workspace/lobby/config-registry?type=skills",
  );
});

test("resolveActiveConfigId keeps valid selections and falls back to the first item", () => {
  const items = [createSkillSummary("skill.outline"), createSkillSummary("skill.chapter")];
  assert.equal(resolveActiveConfigId({ items, selectedId: "skill.chapter" }), "skill.chapter");
  assert.equal(resolveActiveConfigId({ items, selectedId: "skill.unknown" }), "skill.outline");
  assert.equal(resolveActiveConfigId({ items: [], selectedId: "skill.unknown" }), null);
});

test("resolveConfigRegistryRoutePatches normalizes invalid type before list data is ready", () => {
  assert.deepEqual(
    resolveConfigRegistryRoutePatches({
      activeItemId: null,
      hasLoadedList: false,
      routeItemId: "skill.unknown",
      routeType: "invalid",
      type: "skills",
    }),
    { type: "skills" },
  );
  assert.equal(
    resolveConfigRegistryRoutePatches({
      activeItemId: null,
      hasLoadedList: false,
      routeItemId: "skill.unknown",
      routeType: "skills",
      type: "skills",
    }),
    null,
  );
});

test("resolveConfigRegistryRoutePatches validates selected item only after list is loaded", () => {
  assert.deepEqual(
    resolveConfigRegistryRoutePatches({
      activeItemId: "skill.outline",
      hasLoadedList: true,
      routeItemId: "skill.unknown",
      routeType: "skills",
      type: "skills",
    }),
    { item: "skill.outline" },
  );
  assert.deepEqual(
    resolveConfigRegistryRoutePatches({
      activeItemId: null,
      hasLoadedList: true,
      routeItemId: "skill.unknown",
      routeType: "invalid",
      type: "skills",
    }),
    { item: null, type: "skills" },
  );
});

test("parseConfigRegistryDocument rejects malformed and non-object JSON", () => {
  assert.equal(parseConfigRegistryDocument("{").parsed, null);
  const arrayResult = parseConfigRegistryDocument("[]");
  assert.equal(arrayResult.parsed, null);
  assert.equal(arrayResult.errorMessage, "配置内容必须是 JSON 对象。");
  const objectResult = parseConfigRegistryDocument(JSON.stringify(createAgentSummary("agent.writer")));
  assert.deepEqual(objectResult.parsed, createAgentSummary("agent.writer"));
});

function createSkillSummary(id: string): SkillConfigSummary {
  return {
    author: "easyStory",
    category: "story",
    description: "skill summary",
    id,
    input_keys: ["project_setting"],
    model: null,
    name: id,
    output_keys: ["outline"],
    tags: ["story"],
    version: "1.0.0",
  };
}

function createAgentSummary(id: string): AgentConfigSummary {
  return {
    agent_type: "writer",
    author: "easyStory",
    description: "agent summary",
    id,
    mcp_servers: [],
    model: null,
    name: id,
    output_schema_keys: ["content"],
    skill_ids: ["skill.outline"],
    tags: ["writer"],
    version: "1.0.0",
  };
}
