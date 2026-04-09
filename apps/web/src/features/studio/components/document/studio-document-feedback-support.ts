import { getErrorCode, getErrorMessage } from "@/lib/api/client";

const VERSION_CONFLICT_MESSAGE = "当前文稿已发生变化，请刷新最新内容后再保存。";
const DOCUMENT_NOT_FOUND_MESSAGE = "当前文稿不存在，可能已被重命名或删除，请刷新目录后重试。";
const SCHEMA_VALIDATION_PREFIX = "数据层文稿校验失败：";

export function resolveStudioDocumentSaveErrorMessage(error: unknown): string {
  const code = getErrorCode(error);
  if (code === "version_conflict") {
    return VERSION_CONFLICT_MESSAGE;
  }
  if (code === "document_not_found") {
    return DOCUMENT_NOT_FOUND_MESSAGE;
  }
  if (code === "schema_validation_failed") {
    return normalizeSchemaValidationMessage(getErrorMessage(error));
  }
  return getErrorMessage(error);
}

function normalizeSchemaValidationMessage(message: string): string {
  const trimmed = message.trim();
  if (!trimmed) {
    return "数据层文稿校验失败，请修正文稿内容后重试。";
  }
  if (trimmed.startsWith(SCHEMA_VALIDATION_PREFIX)) {
    return trimmed;
  }
  return `${SCHEMA_VALIDATION_PREFIX}${trimmed}`;
}
