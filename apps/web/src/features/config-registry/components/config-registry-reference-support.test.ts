import assert from "node:assert/strict";
import test from "node:test";

import { buildConfigRegistryReferenceFieldState } from "./config-registry-reference-support";

test("reference field state exposes explicit loading and error messages", () => {
  assert.deepEqual(
    buildConfigRegistryReferenceFieldState({
      defaultEmptyMessage: "暂无可选 Skills，可切换到完整配置。",
      errorMessage: null,
      isLoading: true,
      loadingMessage: "正在加载 Skills…",
      options: [],
    }),
    {
      bannerMessage: null,
      bannerTone: null,
      emptyMessage: "正在加载 Skills…",
      options: [],
    },
  );

  assert.deepEqual(
    buildConfigRegistryReferenceFieldState({
      defaultEmptyMessage: "暂无可选 Skills，可切换到完整配置。",
      errorMessage: "Skills 列表加载失败：403 Forbidden",
      isLoading: false,
      loadingMessage: "正在加载 Skills…",
      options: [{ label: "Draft (skill.draft)", value: "skill.draft" }],
    }),
    {
      bannerMessage: "Skills 列表加载失败：403 Forbidden",
      bannerTone: "danger",
      emptyMessage: "Skills 列表加载失败：403 Forbidden",
      options: [{ label: "Draft (skill.draft)", value: "skill.draft" }],
    },
  );
});

test("reference field state falls back to normal empty message when ready", () => {
  assert.deepEqual(
    buildConfigRegistryReferenceFieldState({
      defaultEmptyMessage: "暂无可选 MCP。",
      errorMessage: null,
      isLoading: false,
      loadingMessage: "正在加载 MCP…",
      options: [],
    }),
    {
      bannerMessage: null,
      bannerTone: null,
      emptyMessage: "暂无可选 MCP。",
      options: [],
    },
  );
});
