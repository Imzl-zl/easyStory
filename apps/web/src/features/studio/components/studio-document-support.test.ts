import assert from "node:assert/strict";
import test from "node:test";

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
});
