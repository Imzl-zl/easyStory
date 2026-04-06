import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "@/lib/api/client";

import { resolveStudioDocumentSaveErrorMessage } from "./studio-document-feedback-support";

test("resolveStudioDocumentSaveErrorMessage normalizes version conflict to stable Chinese copy", () => {
  const error = new ApiError(
    "目标文稿版本已变化，请重新读取最新内容后再写入。",
    422,
    "目标文稿版本已变化，请重新读取最新内容后再写入。",
    "version_conflict",
  );

  assert.equal(
    resolveStudioDocumentSaveErrorMessage(error),
    "当前文稿已发生变化，请刷新最新内容后再保存。",
  );
});

test("resolveStudioDocumentSaveErrorMessage prefixes schema validation failures", () => {
  const error = new ApiError(
    "目标数据文稿 characters[0].id 必须是非空字符串。",
    422,
    "目标数据文稿 characters[0].id 必须是非空字符串。",
    "schema_validation_failed",
  );

  assert.equal(
    resolveStudioDocumentSaveErrorMessage(error),
    "数据层文稿校验失败：目标数据文稿 characters[0].id 必须是非空字符串。",
  );
});

test("resolveStudioDocumentSaveErrorMessage rewrites missing document into refresh guidance", () => {
  const error = new ApiError(
    "目标文稿不存在",
    404,
    "目标文稿不存在",
    "document_not_found",
  );

  assert.equal(
    resolveStudioDocumentSaveErrorMessage(error),
    "当前文稿不存在，可能已被重命名或删除，请刷新目录后重试。",
  );
});

test("resolveStudioDocumentSaveErrorMessage falls back to the original error message", () => {
  const error = new ApiError("保存失败，请检查网络。", 500, "保存失败，请检查网络。");

  assert.equal(
    resolveStudioDocumentSaveErrorMessage(error),
    "保存失败，请检查网络。",
  );
});
