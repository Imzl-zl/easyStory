import assert from "node:assert/strict";
import test from "node:test";

import {
  applyStudioChatToolCallResult,
  applyStudioChatToolCallStart,
  buildStudioAssistantTurnPayload,
  buildStudioUserRequestContent,
  createStudioChatMessage,
  finalizeStudioChatToolProgress,
  INITIAL_STUDIO_CHAT_SETTINGS,
  resolveStudioAssistantMessageActionState,
  resolveStudioFailedReply,
} from "./studio-chat-support";

test("studio chat payload uses document_context and continuation anchor", () => {
  const messages = [
    createStudioChatMessage("assistant", "上一轮回复"),
    createStudioChatMessage("user", "继续写这一段"),
  ];
  const documentCatalogEntries = [
    {
      binding_version: "binding-chapter-1",
      catalog_version: "catalog-v1",
      content_state: "ready" as const,
      document_kind: "markdown",
      document_ref: "canonical:chapter:001",
      mime_type: "text/markdown",
      path: "正文/第001章.md",
      resource_uri: "project-document://project-1/canonical%3Achapter%3A001",
      schema_id: null,
      source: "chapter" as const,
      title: "第001章",
      updated_at: "2026-04-05T00:00:00Z",
      version: "canonical:chapter:001:version:content-1:2",
      writable: false,
    },
    {
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready" as const,
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file" as const,
      title: "人物",
      updated_at: "2026-04-05T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    },
  ];

  const payload = buildStudioAssistantTurnPayload({
    activeBufferState: {
      base_version: "canonical:chapter:001:version:content-1:2",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    conversationId: "conversation-studio-test",
    currentDocumentPath: "正文/第001章.md",
    documentCatalogEntries,
    latestCompletedRunId: "run-prev-1",
    messages,
    projectId: "project-1",
    selectedContextPaths: ["设定/人物.md", "正文/第001章.md", "设定/人物.md"],
    settings: INITIAL_STUDIO_CHAT_SETTINGS,
  });

  assert.deepEqual(payload.document_context, {
    active_binding_version: "binding-chapter-1",
    active_document_ref: "canonical:chapter:001",
    active_path: "正文/第001章.md",
    active_buffer_state: {
      base_version: "canonical:chapter:001:version:content-1:2",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    catalog_version: "catalog-v1",
    selected_document_refs: ["file:设定/人物.md"],
    selected_paths: ["设定/人物.md"],
  });
  assert.deepEqual(payload.continuation_anchor, {
    previous_run_id: "run-prev-1",
  });
  assert.equal(payload.requested_write_scope, "disabled");
  assert.equal(payload.requested_write_targets, undefined);
});

test("studio chat payload does not infer requested write targets from writable active document", () => {
  const messages = [createStudioChatMessage("user", "把当前设定补一条观察能力。")];
  const documentCatalogEntries = [
    {
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready" as const,
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file" as const,
      title: "人物",
      updated_at: "2026-04-05T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    },
  ];

  const payload = buildStudioAssistantTurnPayload({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    conversationId: "conversation-studio-write",
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries,
    latestCompletedRunId: null,
    messages,
    projectId: "project-1",
    selectedContextPaths: [],
    settings: INITIAL_STUDIO_CHAT_SETTINGS,
  });

  assert.equal(payload.requested_write_scope, "disabled");
  assert.equal(payload.requested_write_targets, undefined);
});

test("studio chat payload uses explicitly requested write targets", () => {
  const messages = [createStudioChatMessage("user", "把当前设定补一条观察能力。")];
  const documentCatalogEntries = [
    {
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready" as const,
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file" as const,
      title: "人物",
      updated_at: "2026-04-05T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    },
  ];

  const payload = buildStudioAssistantTurnPayload({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    conversationId: "conversation-studio-write",
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries,
    latestCompletedRunId: null,
    messages,
    projectId: "project-1",
    requestedWriteTargets: ["file:设定/人物.md"],
    selectedContextPaths: [],
    settings: INITIAL_STUDIO_CHAT_SETTINGS,
  });

  assert.equal(payload.requested_write_scope, "turn");
  assert.deepEqual(payload.requested_write_targets, ["file:设定/人物.md"]);
});

test("studio chat payload replays attachment-enriched user messages across turns", () => {
  const payload = buildStudioAssistantTurnPayload({
    conversationId: "conversation-studio-attachments",
    currentDocumentPath: null,
    latestCompletedRunId: null,
    messages: [
      createStudioChatMessage("user", "我附带了旧文件。", {
        attachments: [{
          id: "file-old",
          name: "旧设定.md",
          size: 12,
        }],
        requestContent: "旧文件正文：人物设定 A",
      }),
      createStudioChatMessage("assistant", "我先看完旧文件。"),
      createStudioChatMessage("user", "我附带了新文件。", {
        attachments: [{
          id: "file-new",
          name: "新设定.md",
          size: 34,
        }],
        requestContent: "新文件正文：人物设定 B",
      }),
    ],
    projectId: "project-1",
    selectedContextPaths: [],
    settings: INITIAL_STUDIO_CHAT_SETTINGS,
  });

  assert.deepEqual(payload.messages, [
    { content: "旧文件正文：人物设定 A", role: "user" },
    { content: "我先看完旧文件。", role: "assistant" },
    { content: "新文件正文：人物设定 B", role: "user" },
  ]);
});

test("studio user request content only appends attachment context", () => {
  const requestContent = buildStudioUserRequestContent({
    attachments: [
      {
        content: "人物设定：林渊，冷静克制。",
        id: "file-1",
        name: "人物设定.md",
        size: 42,
      },
    ],
    message: "请继续写第一章开头。",
  });

  assert.match(requestContent, /请继续写第一章开头/);
  assert.match(requestContent, /附带的文件/);
  assert.doesNotMatch(requestContent, /当前文稿/);
  assert.doesNotMatch(requestContent, /额外参考路径/);
});

test("studio chat payload rejects missing document catalog snapshot", () => {
  const messages = [createStudioChatMessage("user", "继续写这一段")];

  assert.throws(
    () =>
      buildStudioAssistantTurnPayload({
        activeBufferState: {
          base_version: "canonical:chapter:001:version:content-1:2",
          buffer_hash: "fnv1a64:abc123",
          dirty: false,
          source: "studio_editor",
        },
        conversationId: "conversation-studio-test",
        currentDocumentPath: "正文/第001章.md",
        latestCompletedRunId: null,
        messages,
        projectId: "project-1",
        selectedContextPaths: [],
        settings: INITIAL_STUDIO_CHAT_SETTINGS,
      }),
    /目录快照尚未就绪/,
  );
});

test("studio chat payload requires the last message to be from the user", () => {
  const messages = [
    createStudioChatMessage("user", "先说一段"),
    createStudioChatMessage("assistant", "我先补一段"),
  ];

  assert.throws(
    () =>
      buildStudioAssistantTurnPayload({
        conversationId: "conversation-studio-test",
        currentDocumentPath: null,
        latestCompletedRunId: null,
        messages,
        projectId: "project-1",
        selectedContextPaths: [],
        settings: INITIAL_STUDIO_CHAT_SETTINGS,
      }),
    /latest user message/,
  );
});

test("studio failed reply replaces pending placeholder with explicit backend error", () => {
  assert.equal(
    resolveStudioFailedReply(
      "正在贴合当前文稿整理思路…",
      "模型连接“薄荷codex”尚未通过“验证工具”，当前不能启用项目工具。",
    ),
    "模型连接“薄荷codex”尚未通过“验证工具”，当前不能启用项目工具。",
  );
});

test("studio failed reply keeps partial content when stream was interrupted after output", () => {
  assert.equal(
    resolveStudioFailedReply(
      "我已经读到了项目说明。",
      "实时回复意外中断，请重试。",
    ),
    "我已经读到了项目说明。\n\n这次回复中断了，你可以重新发送。",
  );
});

test("studio assistant error message action state uses visible content and disables document actions", () => {
  const actionState = resolveStudioAssistantMessageActionState({
    content: "这次回复中断了，你可以重新发送。",
    rawMarkdown: "# 旧正文",
    role: "assistant",
    status: "error",
  });

  assert.deepEqual(actionState, {
    actionContent: "这次回复中断了，你可以重新发送。",
    copyLabel: "复制内容",
    documentMatchSource: null,
    showCopyAction: true,
    showDocumentActions: false,
  });
});

test("studio assistant completed message action state keeps markdown document actions", () => {
  const actionState = resolveStudioAssistantMessageActionState({
    content: "已整理完成。",
    rawMarkdown: "# 标题\n\n正文",
    role: "assistant",
    status: undefined,
  });

  assert.deepEqual(actionState, {
    actionContent: "# 标题\n\n正文",
    copyLabel: "复制 Markdown",
    documentMatchSource: "# 标题\n\n正文",
    showCopyAction: true,
    showDocumentActions: true,
  });
});

test("studio chat tool progress uses friendly labels and updates result state", () => {
  const assistantMessage = createStudioChatMessage("assistant", "正在贴合当前文稿整理思路…", {
    status: "pending",
  });
  const withStart = applyStudioChatToolCallStart([assistantMessage], assistantMessage.id, {
    target_summary: {
      path: "设定/人物.md",
    },
    tool_call_id: "call-1",
    tool_name: "project.read_documents",
  });
  const withResult = applyStudioChatToolCallResult(withStart, assistantMessage.id, {
    result_summary: {
      document_count: 1,
    },
    status: "completed",
    tool_call_id: "call-1",
    tool_name: "project.read_documents",
  });

  assert.deepEqual(withStart[0]?.toolProgress, [{
    detail: "设定/人物.md",
    label: "读取文稿",
    statusLabel: "处理中",
    toolCallId: "call-1",
    tone: "running",
  }]);
  assert.deepEqual(withResult[0]?.toolProgress, [{
    detail: "1 篇文稿",
    label: "读取文稿",
    statusLabel: "已完成",
    toolCallId: "call-1",
    tone: "success",
  }]);
});

test("studio chat tool progress finalizes running entries without rewriting terminal ones", () => {
  assert.deepEqual(
    finalizeStudioChatToolProgress([
      {
        detail: "设定/人物.md",
        label: "读取文稿",
        statusLabel: "处理中",
        toolCallId: "call-1",
        tone: "running",
      },
      {
        detail: "1 篇文稿",
        label: "检索文稿",
        statusLabel: "已完成",
        toolCallId: "call-2",
        tone: "success",
      },
    ], "interrupted"),
    [
      {
        detail: "设定/人物.md",
        label: "读取文稿",
        statusLabel: "已中断",
        toolCallId: "call-1",
        tone: "muted",
      },
      {
        detail: "1 篇文稿",
        label: "检索文稿",
        statusLabel: "已完成",
        toolCallId: "call-2",
        tone: "success",
      },
    ],
  );
});
