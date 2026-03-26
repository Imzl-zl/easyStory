import assert from "node:assert/strict";
import test from "node:test";

import type { AgentConfigSummary, HookConfigSummary, SkillConfigSummary } from "@/lib/api/types";

import {
  filterConfigRegistryItems,
  isConfigRegistryFormSupported,
  listConfigRegistryFilterTags,
  parseConfigRegistryCsvParam,
  resolveConfigRegistryEditorMode,
  resolveConfigRegistryRoutePatches,
  resolveConfigRegistrySortValue,
  resolveConfigRegistryStatusValue,
  serializeConfigRegistryEditorMode,
  serializeConfigRegistrySortValue,
  serializeConfigRegistryStatusValue,
  supportsConfigRegistryStatusFilter,
  supportsConfigRegistryTagFilter,
} from "./config-registry-state-support";

test("editor mode falls back to form for supported types and forces workflow json", () => {
  assert.equal(resolveConfigRegistryEditorMode("skills", null), "form");
  assert.equal(resolveConfigRegistryEditorMode("skills", "json"), "json");
  assert.equal(resolveConfigRegistryEditorMode("workflows", null), "json");
  assert.equal(isConfigRegistryFormSupported("workflows"), false);
  assert.equal(serializeConfigRegistryEditorMode("skills", "form"), null);
  assert.equal(serializeConfigRegistryEditorMode("workflows", "json"), "json");
});

test("csv, sort and status params normalize to supported values", () => {
  assert.deepEqual(parseConfigRegistryCsvParam("story, review, story"), ["story", "review", "story"]);
  assert.equal(resolveConfigRegistrySortValue("name_desc"), "name_desc");
  assert.equal(resolveConfigRegistrySortValue("bad"), "name_asc");
  assert.equal(serializeConfigRegistrySortValue("name_asc"), null);
  assert.equal(resolveConfigRegistryStatusValue("hooks", "enabled"), "enabled");
  assert.equal(resolveConfigRegistryStatusValue("skills", "enabled"), "all");
  assert.equal(serializeConfigRegistryStatusValue("hooks", "disabled"), "disabled");
  assert.equal(serializeConfigRegistryStatusValue("skills", "enabled"), null);
});

test("support flags and available tags follow type boundaries", () => {
  assert.equal(supportsConfigRegistryTagFilter("skills"), true);
  assert.equal(supportsConfigRegistryTagFilter("hooks"), false);
  assert.equal(supportsConfigRegistryStatusFilter("mcp_servers"), true);
  assert.equal(supportsConfigRegistryStatusFilter("agents"), false);
  assert.deepEqual(listConfigRegistryFilterTags([createSkillSummary("skill.a"), createAgentSummary("agent.b")], "skills"), [
    "review",
    "story",
  ]);
});

test("filterConfigRegistryItems applies query, tag, status and sort", () => {
  assert.deepEqual(
    filterConfigRegistryItems({
      items: [createSkillSummary("skill.alpha"), createSkillSummary("skill.beta")],
      query: "beta",
      sort: "name_asc",
      status: "all",
      tags: [],
      type: "skills",
    }).map((item) => item.id),
    ["skill.beta"],
  );
  assert.deepEqual(
    filterConfigRegistryItems({
      items: [createSkillSummary("skill.alpha"), createSkillSummary("skill.beta")],
      query: "",
      sort: "name_desc",
      status: "all",
      tags: ["review"],
      type: "skills",
    }).map((item) => item.id),
    ["skill.beta"],
  );
  assert.deepEqual(
    filterConfigRegistryItems({
      items: [createHookSummary("hook.enabled", true), createHookSummary("hook.disabled", false)],
      query: "",
      sort: "name_asc",
      status: "enabled",
      tags: [],
      type: "hooks",
    }).map((item) => item.id),
    ["hook.enabled"],
  );
});

test("route patches normalize mode and type-specific filters", () => {
  assert.deepEqual(
    resolveConfigRegistryRoutePatches({
      activeItemId: null,
      hasLoadedList: false,
      mode: "form",
      query: "",
      routeItemId: "skill.a",
      routeMode: "bad",
      routeQuery: "",
      routeSort: "bad",
      routeStatus: "enabled",
      routeTags: "story",
      routeType: "invalid",
      sort: "name_asc",
      status: "all",
      tags: ["story"],
      type: "skills",
    }),
    {
      mode: null,
      q: null,
      sort: null,
      status: null,
      type: "skills",
    },
  );
  assert.deepEqual(
    resolveConfigRegistryRoutePatches({
      activeItemId: "workflow.a",
      hasLoadedList: true,
      mode: "json",
      query: "",
      routeItemId: null,
      routeMode: null,
      routeQuery: null,
      routeSort: null,
      routeStatus: null,
      routeTags: "story",
      routeType: "workflows",
      sort: "name_asc",
      status: "all",
      tags: ["story"],
      type: "workflows",
    }),
    { item: "workflow.a", mode: "json" },
  );
});

function createSkillSummary(id: string): SkillConfigSummary {
  return {
    author: "easyStory",
    category: "story",
    description: "skill summary",
    id,
    input_keys: ["project_setting"],
    model: null,
    name: id === "skill.beta" ? "Beta" : "Alpha",
    output_keys: ["outline"],
    tags: id === "skill.beta" ? ["story", "review"] : ["story"],
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
    output_schema_keys: [],
    skill_ids: [],
    tags: ["review"],
    version: "1.0.0",
  };
}

function createHookSummary(id: string, enabled: boolean): HookConfigSummary {
  return {
    action_type: "script",
    author: null,
    description: "hook summary",
    enabled,
    has_condition: false,
    id,
    name: id,
    priority: 10,
    retry_enabled: false,
    timeout: 30,
    trigger_event: "before_generate",
    trigger_node_types: ["generate"],
    version: "1.0.0",
  };
}
