import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioWriteIntentNotice,
  resolveStudioCurrentWriteTarget,
  resolveStudioRequestedWriteTargets,
  resolveStudioWriteSendBlockReason,
  resolveStudioWriteToggleDisabled,
} from "./studio-chat-write-support";

test("studio current write target is available only for writable active document with trusted buffer", () => {
  const target = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries: [{
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file",
      title: "人物",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    }],
  });

  assert.equal(target.available, true);
  assert.equal(target.disabledReason, null);
  assert.equal(target.targetDocumentRef, "file:设定/人物.md");
  assert.equal(
    buildStudioWriteIntentNotice(target, true),
    "本轮只允许助手改写当前文稿：设定/人物.md",
  );
});

test("studio current write target remains unavailable for read-only active document", () => {
  const target = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "canonical:chapter:001:version:1",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    currentDocumentPath: "正文/第001章.md",
    documentCatalogEntries: [{
      binding_version: "binding-chapter-1",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "canonical:chapter:001",
      mime_type: "text/markdown",
      path: "正文/第001章.md",
      resource_uri: "project-document://project-1/canonical%3Achapter%3A001",
      schema_id: null,
      source: "chapter",
      title: "第001章",
      updated_at: "2026-04-08T00:00:00Z",
      version: "canonical:chapter:001:version:1",
      writable: false,
    }],
  });

  assert.equal(target.available, false);
  assert.equal(target.disabledReason, "当前文稿是只读内容，助手本轮只能读取。");
  assert.equal(
    buildStudioWriteIntentNotice(target, false),
    "当前文稿是只读内容，助手本轮只能读取。",
  );
});

test("studio current write target requires a clean trusted buffer snapshot", () => {
  const target = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: true,
      source: "studio_editor",
    },
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries: [{
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file",
      title: "人物",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    }],
  });

  assert.equal(target.available, false);
  assert.equal(target.disabledReason, "先保存当前文稿，再允许助手改写。");
});

test("studio current write target requires base version aligned with the current catalog entry", () => {
  const target = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "sha256:cast-old",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries: [{
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file",
      title: "人物",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:cast-new",
      writable: true,
    }],
  });

  assert.equal(target.available, false);
  assert.equal(target.disabledReason, "当前文稿基线已变化，请先重新加载当前文稿后再试。");
});

test("studio current write target follows catalog query errors even when stale entries remain", () => {
  const target = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    currentDocumentPath: "设定/人物.md",
    documentCatalogErrorMessage: "当前文稿目录快照拉取失败，请稍后重试。",
    documentCatalogEntries: [{
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file",
      title: "人物",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    }],
  });

  assert.equal(target.available, false);
  assert.equal(target.disabledReason, "当前文稿目录快照拉取失败，请稍后重试。");
});

test("studio write support blocks send when explicit write intent no longer has a valid target", () => {
  const unavailableTarget = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: true,
      source: "studio_editor",
    },
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries: [{
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file",
      title: "人物",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    }],
  });

  assert.equal(
    resolveStudioWriteSendBlockReason({
      enabled: true,
      writeTarget: unavailableTarget,
    }),
    "先保存当前文稿，再允许助手改写。",
  );
  assert.deepEqual(
    resolveStudioRequestedWriteTargets({
      enabled: true,
      writeTarget: unavailableTarget,
    }),
    null,
  );
  assert.equal(
    buildStudioWriteIntentNotice(unavailableTarget, true),
    "先保存当前文稿，再允许助手改写。",
  );
  assert.equal(
    resolveStudioWriteToggleDisabled({
      enabled: true,
      writeTargetDisabledReason: unavailableTarget.disabledReason,
    }),
    false,
  );
  assert.equal(
    resolveStudioWriteToggleDisabled({
      enabled: false,
      writeTargetDisabledReason: unavailableTarget.disabledReason,
    }),
    true,
  );
});

test("studio write support only sends requested write target when explicit intent remains valid", () => {
  const availableTarget = resolveStudioCurrentWriteTarget({
    activeBufferState: {
      base_version: "sha256:cast",
      buffer_hash: "fnv1a64:abc123",
      dirty: false,
      source: "studio_editor",
    },
    currentDocumentPath: "设定/人物.md",
    documentCatalogEntries: [{
      binding_version: "binding-cast",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/人物.md",
      mime_type: "text/markdown",
      path: "设定/人物.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%BA%BA%E7%89%A9.md",
      schema_id: null,
      source: "file",
      title: "人物",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:cast",
      writable: true,
    }],
  });

  assert.equal(
    resolveStudioWriteSendBlockReason({
      enabled: true,
      writeTarget: availableTarget,
    }),
    null,
  );
  assert.deepEqual(
    resolveStudioRequestedWriteTargets({
      enabled: true,
      writeTarget: availableTarget,
    }),
    ["file:设定/人物.md"],
  );
});
