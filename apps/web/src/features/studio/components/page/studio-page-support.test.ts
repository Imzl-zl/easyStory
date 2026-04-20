import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioChatGridTemplateColumns,
  buildStudioDocumentEntryPath,
  buildStudioDocumentTree,
  buildStudioPathWithParams,
  clampStudioChatSidebarWidth,
  findClosestRemainingFilePath,
  getStudioPanelLabel,
  listStudioPanelOptions,
  resolveDefaultStudioChatSidebarWidth,
  resolveDefaultDocumentPathFromPanel,
  resolveStudioChatLayoutMode,
  resolveStudioDocumentPath,
  resolveStudioChapterListState,
  resolveSelectedChapterNumber,
  resolveStudioPanel,
} from "@/features/studio/components/page/studio-page-support";

test("resolveStudioPanel falls back to overview for invalid values", () => {
  assert.equal(resolveStudioPanel("chapter"), "chapter");
  assert.equal(resolveStudioPanel("invalid"), "overview");
  assert.equal(resolveStudioPanel(null), "overview");
});

test("getStudioPanelLabel returns the visible label for each panel", () => {
  assert.equal(getStudioPanelLabel("overview"), "项目说明");
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

test("studio chat sidebar width clamps within desktop bounds", () => {
  assert.equal(clampStudioChatSidebarWidth(200, 1024), 320);
  assert.equal(clampStudioChatSidebarWidth(999, 1024), 368);
  assert.equal(clampStudioChatSidebarWidth(520, 1440), 520);
  assert.equal(clampStudioChatSidebarWidth(1200, 1440), 760);
});

test("studio chat sidebar default width follows previous layout targets", () => {
  assert.equal(resolveDefaultStudioChatSidebarWidth(1024), 368);
  assert.equal(resolveDefaultStudioChatSidebarWidth(1280), 408);
});

test("studio chat layout mode switches from default to compact to icon", () => {
  assert.equal(resolveStudioChatLayoutMode(520), "default");
  assert.equal(resolveStudioChatLayoutMode(400), "compact");
  assert.equal(resolveStudioChatLayoutMode(360), "icon");
  assert.equal(resolveStudioChatLayoutMode(320), "icon");
});

test("studio chat grid template columns only apply when chat width is available on desktop", () => {
  assert.equal(
    buildStudioChatGridTemplateColumns({ chatOpen: true, chatWidth: 480, containerWidth: 1280 }),
    "244px minmax(0, 1fr) 480px",
  );
  assert.equal(
    buildStudioChatGridTemplateColumns({ chatOpen: true, chatWidth: 200, containerWidth: 1024 }),
    "236px minmax(0, 1fr) 320px",
  );
  assert.equal(
    buildStudioChatGridTemplateColumns({ chatOpen: false, chatWidth: 480, containerWidth: 1280 }),
    null,
  );
  assert.equal(
    buildStudioChatGridTemplateColumns({ chatOpen: true, chatWidth: null, containerWidth: 1280 }),
    null,
  );
  assert.equal(
    buildStudioChatGridTemplateColumns({ chatOpen: true, chatWidth: 360, containerWidth: 900 }),
    null,
  );
});

test("resolveDefaultDocumentPathFromPanel maps explicit panel routes to canonical documents", () => {
  const chapters = [
    { chapter_number: 2, status: "approved" },
    { chapter_number: 7, status: "stale" },
  ] as const;

  assert.equal(resolveDefaultDocumentPathFromPanel("overview", undefined, null), "项目说明.md");
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

test("buildStudioDocumentEntryPath supports creating entries at project root", () => {
  assert.equal(buildStudioDocumentEntryPath("", "项目说明", "file"), "项目说明.md");
  assert.equal(buildStudioDocumentEntryPath("", "附录", "folder"), "附录");
});

test("buildStudioDocumentEntryPath preserves explicit json file names", () => {
  assert.equal(buildStudioDocumentEntryPath("数据层", "人物关系", "file"), "数据层/人物关系.json");
  assert.equal(buildStudioDocumentEntryPath("数据层", "势力关系.json", "file"), "数据层/势力关系.json");
  assert.equal(buildStudioDocumentEntryPath("设定", "人物", "file"), "设定/人物.md");
  assert.equal(buildStudioDocumentEntryPath("设定", "人物.json", "folder"), null);
});

test("buildStudioDocumentEntryPath normalizes chapter names under content roots", () => {
  assert.equal(buildStudioDocumentEntryPath("正文", "1", "file"), "正文/第001章.md");
  assert.equal(buildStudioDocumentEntryPath("正文/第一卷", "第7章", "file"), "正文/第一卷/第007章.md");
  assert.equal(buildStudioDocumentEntryPath("正文", "章节一", "file"), null);
});

test("buildStudioDocumentTree keeps fixed slots while ordering template roots around them", () => {
  const tree = buildStudioDocumentTree(
    [{ chapter_number: 2, status: "draft" }] as never,
    [
      {
        children: [],
        label: "项目说明.md",
        node_type: "file",
        path: "项目说明.md",
      },
      {
        children: [
          {
            children: [],
            label: "世界观.md",
            node_type: "file",
            path: "设定/世界观.md",
          },
        ],
        label: "设定",
        node_type: "folder",
        path: "设定",
      },
      {
        children: [
          {
            children: [],
            label: "章节规划.md",
            node_type: "file",
            path: "大纲/章节规划.md",
          },
        ],
        label: "大纲",
        node_type: "folder",
        path: "大纲",
      },
      {
        children: [],
        label: "数据层",
        node_type: "folder",
        path: "数据层",
      },
      {
        children: [],
        label: "附录",
        node_type: "folder",
        path: "附录",
      },
    ] as never,
  );

  assert.deepEqual(
    tree.map((node) => node.path),
    ["项目说明.md", "设定", "数据层", "大纲", "正文", "附录"],
  );
  assert.equal(tree[1]?.canDelete, undefined);
  assert.equal(tree[3]?.children?.[0]?.path, "大纲/总大纲.md");
  assert.equal(tree[3]?.children?.[2]?.path, "大纲/章节规划.md");
});

test("buildStudioDocumentTree nests chapter documents under custom content folders", () => {
  const tree = buildStudioDocumentTree(
    [
      { chapter_number: 1, status: "draft" },
      { chapter_number: 2, status: "stale" },
      { chapter_number: 3, status: "approved" },
    ] as never,
    [
      {
        children: [
          {
            children: [
              {
                children: [],
                label: "第001章.md",
                node_type: "file",
                path: "正文/第一卷/第001章.md",
              },
              {
                children: [],
                label: "第002章.md",
                node_type: "file",
                path: "正文/第一卷/第002章.md",
              },
            ],
            label: "第一卷",
            node_type: "folder",
            path: "正文/第一卷",
          },
        ],
        label: "正文",
        node_type: "folder",
        path: "正文",
      },
    ] as never,
  );

  const contentRoot = tree.find((node) => node.path === "正文");
  assert.ok(contentRoot);
  assert.equal(contentRoot?.children?.[0]?.path, "正文/第一卷");
  assert.equal(contentRoot?.children?.[0]?.canDelete, false);
  assert.equal(contentRoot?.children?.[0]?.children?.[0]?.path, "正文/第一卷/第001章.md");
  assert.equal(contentRoot?.children?.[0]?.children?.[0]?.origin, "database");
  assert.equal(contentRoot?.children?.[1]?.path, "正文/第003章.md");
});

test("findClosestRemainingFilePath prefers nearby files after deletion", () => {
  const tree = buildStudioDocumentTree(
    [{ chapter_number: 1, status: "draft" }] as never,
    [
      {
        children: [],
        label: "项目说明.md",
        node_type: "file",
        path: "项目说明.md",
      },
      {
        children: [
          {
            children: [],
            label: "线索.md",
            node_type: "file",
            path: "附录/线索.md",
          },
          {
            children: [],
            label: "设定补充.md",
            node_type: "file",
            path: "附录/设定补充.md",
          },
        ],
        label: "附录",
        node_type: "folder",
        path: "附录",
      },
    ] as never,
  );

  assert.equal(
    findClosestRemainingFilePath(tree, "附录/线索.md", "附录/线索.md"),
    "附录/设定补充.md",
  );
  assert.equal(
    findClosestRemainingFilePath(tree, "附录/设定补充.md", "附录/设定补充.md"),
    "附录/线索.md",
  );
});

test("resolveStudioDocumentPath waits for tree readiness and falls back when raw path is missing", () => {
  const tree = buildStudioDocumentTree(
    [] as never,
    [
      {
        children: [],
        label: "项目说明.md",
        node_type: "file",
        path: "项目说明.md",
      },
      {
        children: [],
        label: "附录",
        node_type: "folder",
        path: "附录",
      },
    ] as never,
  );

  assert.equal(resolveStudioDocumentPath("项目说明.md", tree, false, "项目说明.md"), null);
  assert.equal(resolveStudioDocumentPath("项目说明.md", tree, true, "项目说明.md"), "项目说明.md");
  assert.equal(resolveStudioDocumentPath("附录/旧文件.md", tree, true, "项目说明.md"), "项目说明.md");
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
    ["overview", "outline", "opening-plan", "chapter"],
  );
});
