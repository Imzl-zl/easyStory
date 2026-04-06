import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioAssistantTurnPayload,
  buildStudioUserRequestContent,
  createStudioChatMessage,
  INITIAL_STUDIO_CHAT_SETTINGS,
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
