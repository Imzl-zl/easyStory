import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient } from "@tanstack/react-query";

import {
  buildStudioActiveBufferState,
  buildStudioBufferHash,
} from "./studio-document-buffer-support";
import {
  buildStudioDocumentCatalogQueryKey,
  buildStudioDocumentCatalogVersion,
} from "./studio-document-catalog-support";
import {
  buildStudioDocumentQueryKey,
  resolveStudioDocumentTarget,
  syncStudioDocumentQueries,
} from "./studio-document-support";

test("resolveStudioDocumentTarget keeps canonical content paths on database-backed targets", () => {
  assert.deepEqual(resolveStudioDocumentTarget("大纲/总大纲.md"), {
    kind: "outline",
    path: "大纲/总大纲.md",
  });
  assert.deepEqual(resolveStudioDocumentTarget("大纲/开篇设计.md"), {
    kind: "opening_plan",
    path: "大纲/开篇设计.md",
  });
  assert.deepEqual(resolveStudioDocumentTarget("正文/第007章.md"), {
    chapterNumber: 7,
    kind: "chapter",
    path: "正文/第007章.md",
  });
  assert.deepEqual(resolveStudioDocumentTarget("正文/第一卷/第008章.md"), {
    chapterNumber: 8,
    kind: "chapter",
    path: "正文/第一卷/第008章.md",
  });
});

test("resolveStudioDocumentTarget keeps non-canonical markdown paths on file-backed targets", () => {
  assert.deepEqual(resolveStudioDocumentTarget("设定/世界观.md"), {
    kind: "file",
    path: "设定/世界观.md",
  });
  assert.deepEqual(resolveStudioDocumentTarget("附录/灵感碎片.md"), {
    kind: "file",
    path: "附录/灵感碎片.md",
  });
  assert.deepEqual(resolveStudioDocumentTarget("数据层/人物关系.json"), {
    kind: "file",
    path: "数据层/人物关系.json",
  });
});

test("buildStudioActiveBufferState produces a stable editor snapshot", () => {
  const firstHash = buildStudioBufferHash("林渊在雨夜里停下脚步。");
  const secondHash = buildStudioBufferHash("林渊在雨夜里停下脚步。");
  const changedHash = buildStudioBufferHash("林渊在雨夜里加快脚步。");

  assert.equal(firstHash, secondHash);
  assert.notEqual(firstHash, changedHash);
  assert.match(firstHash, /^fnv1a64:[0-9a-f]{16}$/);
  assert.deepEqual(
    buildStudioActiveBufferState({
      baseVersion: "canonical:chapter:007:version:content-chapter-7:5",
      content: "林渊在雨夜里停下脚步。",
      dirty: true,
    }),
    {
      base_version: "canonical:chapter:007:version:content-chapter-7:5",
      buffer_hash: firstHash,
      dirty: true,
      source: "studio_editor",
    },
  );
});

test("syncStudioDocumentQueries keeps file document catalog snapshot aligned after save", async () => {
  const queryClient = new QueryClient();
  queryClient.setQueryData(
    buildStudioDocumentCatalogQueryKey("project-1"),
    [
      {
        binding_version: "binding-world",
        catalog_version: "catalog-v1",
        content_state: "ready",
        document_kind: "markdown",
        document_ref: "file:设定/世界观.md",
        mime_type: "text/markdown",
        path: "设定/世界观.md",
        resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%B8%96%E7%95%8C%E8%A7%82.md",
        schema_id: null,
        source: "file",
        title: "世界观",
        updated_at: "2026-04-08T00:00:00Z",
        version: "sha256:old-world",
        writable: true,
      },
      {
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
      },
    ],
  );

  const expectedCatalogVersion = await buildStudioDocumentCatalogVersion([
    {
      binding_version: "binding-world",
      catalog_version: "catalog-v1",
      content_state: "ready",
      document_kind: "markdown",
      document_ref: "file:设定/世界观.md",
      mime_type: "text/markdown",
      path: "设定/世界观.md",
      resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%B8%96%E7%95%8C%E8%A7%82.md",
      schema_id: null,
      source: "file",
      title: "世界观",
      updated_at: "2026-04-08T00:00:00Z",
      version: "sha256:new-world",
      writable: true,
    },
    {
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
    },
  ]);

  await syncStudioDocumentQueries(queryClient, "project-1", {
    content: "新的世界观内容",
    path: "设定/世界观.md",
    saveNoun: "文件",
    storageKind: "file",
    target: { kind: "file", path: "设定/世界观.md" },
    title: "世界观",
    version: "sha256:new-world",
  });

  assert.deepEqual(
    queryClient.getQueryData(buildStudioDocumentQueryKey("project-1", "设定/世界观.md")),
    {
      content: "新的世界观内容",
      path: "设定/世界观.md",
      saveNoun: "文件",
      storageKind: "file",
      target: { kind: "file", path: "设定/世界观.md" },
      title: "世界观",
      version: "sha256:new-world",
    },
  );
  assert.deepEqual(
    queryClient.getQueryData(buildStudioDocumentCatalogQueryKey("project-1")),
    [
      {
        binding_version: "binding-world",
        catalog_version: expectedCatalogVersion,
        content_state: "ready",
        document_kind: "markdown",
        document_ref: "file:设定/世界观.md",
        mime_type: "text/markdown",
        path: "设定/世界观.md",
        resource_uri: "project-document://project-1/file%3A%E8%AE%BE%E5%AE%9A%2F%E4%B8%96%E7%95%8C%E8%A7%82.md",
        schema_id: null,
        source: "file",
        title: "世界观",
        updated_at: "2026-04-08T00:00:00Z",
        version: "sha256:new-world",
        writable: true,
      },
      {
        binding_version: "binding-cast",
        catalog_version: expectedCatalogVersion,
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
      },
    ],
  );
});
