import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioPathWithParams,
  getStudioPanelLabel,
  listStudioPanelOptions,
  resolveDefaultDocumentPathFromPanel,
  resolveStudioChapterListState,
  resolveSelectedChapterNumber,
  resolveStudioPanel,
} from "./studio-page-support";

test("resolveStudioPanel falls back to setting for invalid values", () => {
  assert.equal(resolveStudioPanel("chapter"), "chapter");
  assert.equal(resolveStudioPanel("invalid"), "setting");
  assert.equal(resolveStudioPanel(null), "setting");
});

test("getStudioPanelLabel returns the visible label for each panel", () => {
  assert.equal(getStudioPanelLabel("setting"), "设定");
  assert.equal(getStudioPanelLabel("outline"), "大纲");
  assert.equal(getStudioPanelLabel("opening-plan"), "开篇设计");
  assert.equal(getStudioPanelLabel("chapter"), "章节");
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

test("resolveDefaultDocumentPathFromPanel maps explicit panel routes to canonical documents", () => {
  const chapters = [
    { chapter_number: 2, status: "approved" },
    { chapter_number: 7, status: "stale" },
  ] as const;

  assert.equal(resolveDefaultDocumentPathFromPanel("setting", undefined, null), "设定/世界观.md");
  assert.equal(resolveDefaultDocumentPathFromPanel("outline", undefined, null), "大纲/总大纲.md");
  assert.equal(
    resolveDefaultDocumentPathFromPanel("opening-plan", undefined, null),
    "大纲/开篇设计.md",
  );
  assert.equal(
    resolveDefaultDocumentPathFromPanel("chapter", chapters as never, null),
    "正文/第007章.md",
  );
  assert.equal(
    resolveDefaultDocumentPathFromPanel("chapter", chapters as never, "2"),
    "正文/第002章.md",
  );
  assert.equal(resolveDefaultDocumentPathFromPanel("chapter", [] as never, null), null);
  assert.equal(resolveDefaultDocumentPathFromPanel(null, chapters as never, null), null);
  assert.equal(resolveDefaultDocumentPathFromPanel("invalid", chapters as never, null), null);
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
