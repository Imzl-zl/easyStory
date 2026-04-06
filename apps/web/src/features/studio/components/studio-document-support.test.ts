import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioActiveBufferState,
  buildStudioBufferHash,
} from "./studio-document-buffer-support";
import { resolveStudioDocumentTarget } from "./studio-document-support";

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
