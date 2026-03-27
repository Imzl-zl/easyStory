import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioPathWithParams,
  listStudioPanelOptions,
  resolveStudioChapterListState,
  resolveSelectedChapterNumber,
  resolveStudioPanel,
} from "./studio-page-support";

test("resolveStudioPanel falls back to setting for invalid values", () => {
  assert.equal(resolveStudioPanel("chapter"), "chapter");
  assert.equal(resolveStudioPanel("invalid"), "setting");
  assert.equal(resolveStudioPanel(null), "setting");
});

test("buildStudioPathWithParams removes empty values without leaving trailing question mark", () => {
  assert.equal(
    buildStudioPathWithParams("/workspace/project/p1/studio", "panel=chapter&versionPanel=1", {
      panel: null,
      versionPanel: null,
    }),
    "/workspace/project/p1/studio",
  );
  assert.equal(
    buildStudioPathWithParams("/workspace/project/p1/studio", "panel=chapter", {
      chapter: "2",
      panel: "chapter",
    }),
    "/workspace/project/p1/studio?panel=chapter&chapter=2",
  );
});

test("resolveSelectedChapterNumber prefers explicit chapter, then first stale, then first chapter", () => {
  const chapters = [
    { chapter_number: 1, status: "approved" },
    { chapter_number: 2, status: "stale" },
  ] as const;
  assert.equal(resolveSelectedChapterNumber(chapters as never, "1"), 1);
  assert.equal(resolveSelectedChapterNumber(chapters as never, null), 2);
  assert.equal(resolveSelectedChapterNumber([{ chapter_number: 3, status: "draft" }] as never, null), 3);
});

test("resolveStudioChapterListState distinguishes loading, error, empty and ready", () => {
  assert.equal(
    resolveStudioChapterListState({
      chapters: undefined,
      errorMessage: null,
      isLoading: true,
    }),
    "loading",
  );
  assert.equal(
    resolveStudioChapterListState({
      chapters: undefined,
      errorMessage: "加载失败",
      isLoading: false,
    }),
    "error",
  );
  assert.equal(
    resolveStudioChapterListState({
      chapters: [],
      errorMessage: null,
      isLoading: false,
    }),
    "empty",
  );
  assert.equal(
    resolveStudioChapterListState({
      chapters: [{ chapter_number: 1, status: "draft" }] as never,
      errorMessage: null,
      isLoading: false,
    }),
    "ready",
  );
});

test("listStudioPanelOptions keeps the expected top tab order", () => {
  assert.deepEqual(
    listStudioPanelOptions().map((item) => item.key),
    ["setting", "outline", "opening-plan", "chapter"],
  );
});
