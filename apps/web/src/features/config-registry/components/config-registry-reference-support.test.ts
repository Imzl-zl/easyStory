import assert from "node:assert/strict";
import test from "node:test";

import { buildConfigRegistryReferenceFieldState } from "./config-registry-reference-support";

test("reference field state exposes explicit loading and error messages", () => {
  assert.deepEqual(
    buildConfigRegistryReferenceFieldState({
      defaultEmptyMessage: "暂无可用 Skill。",
      errorMessage: null,
      isLoading: true,
      loadingMessage: "正在加载可绑定 Skill…",
      options: [],
    }),
    {
      bannerMessage: null,
      bannerTone: null,
      emptyMessage: "正在加载可绑定 Skill…",
      options: [],
    },
  );

  assert.deepEqual(
    buildConfigRegistryReferenceFieldState({
      defaultEmptyMessage: "暂无可用 Skill。",
      errorMessage: "Skill 列表加载失败：403 Forbidden",
      isLoading: false,
      loadingMessage: "正在加载可绑定 Skill…",
      options: [{ label: "Draft (skill.draft)", value: "skill.draft" }],
    }),
    {
      bannerMessage: "Skill 列表加载失败：403 Forbidden",
      bannerTone: "danger",
      emptyMessage: "Skill 列表加载失败：403 Forbidden",
      options: [{ label: "Draft (skill.draft)", value: "skill.draft" }],
    },
  );
});

test("reference field state falls back to normal empty message when ready", () => {
  assert.deepEqual(
    buildConfigRegistryReferenceFieldState({
      defaultEmptyMessage: "暂无可用 MCP Server。",
      errorMessage: null,
      isLoading: false,
      loadingMessage: "正在加载可绑定 MCP Server…",
      options: [],
    }),
    {
      bannerMessage: null,
      bannerTone: null,
      emptyMessage: "暂无可用 MCP Server。",
      options: [],
    },
  );
});
