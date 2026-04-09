"use client";

import type { AssistantActiveBufferState, ProjectDocumentCatalogEntry } from "@/lib/api/types";

const STUDIO_WRITE_BUFFER_SOURCE = "studio_editor";
const STUDIO_WRITE_UNAVAILABLE_MESSAGE = "当前文稿暂时不能启用本轮改写。";

export type StudioCurrentWriteTarget = {
  available: boolean;
  disabledReason: string | null;
  path: string | null;
  targetDocumentRef: string | null;
};

export function resolveStudioCurrentWriteTarget(options: {
  activeBufferState: AssistantActiveBufferState | null;
  currentDocumentPath: string | null;
  documentCatalogErrorMessage?: string | null;
  documentCatalogEntries?: ProjectDocumentCatalogEntry[] | null;
}): StudioCurrentWriteTarget {
  const {
    activeBufferState,
    currentDocumentPath,
    documentCatalogErrorMessage,
    documentCatalogEntries,
  } = options;
  if (!currentDocumentPath) {
    return {
      available: false,
      disabledReason: null,
      path: null,
      targetDocumentRef: null,
    };
  }
  if (documentCatalogErrorMessage) {
    return buildUnavailableWriteTarget(
      currentDocumentPath,
      null,
      documentCatalogErrorMessage,
    );
  }
  if (!documentCatalogEntries?.length) {
    return buildUnavailableWriteTarget(
      currentDocumentPath,
      null,
      "当前文稿目录快照尚未就绪，请稍后重试。",
    );
  }
  const activeEntry = documentCatalogEntries.find((item) => item.path === currentDocumentPath) ?? null;
  if (activeEntry === null) {
    return buildUnavailableWriteTarget(
      currentDocumentPath,
      null,
      `当前文稿目录快照已过期，请刷新后重试：${currentDocumentPath}`,
    );
  }
  if (!activeEntry.writable) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "当前文稿是只读内容，助手本轮只能读取。",
    );
  }
  if (activeBufferState === null) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "当前编辑器缓冲区尚未就绪，请稍后重试。",
    );
  }
  if (activeBufferState.dirty !== false) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "先保存当前文稿，再允许助手改写。",
    );
  }
  if (!isNonEmptyString(activeBufferState.base_version)) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "当前文稿版本快照缺失，请先重新加载文稿。",
    );
  }
  if (activeBufferState.base_version !== activeEntry.version) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "当前文稿基线已变化，请先重新加载当前文稿后再试。",
    );
  }
  if (!isNonEmptyString(activeBufferState.buffer_hash)) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "当前文稿缓冲区哈希缺失，请先保存当前文稿。",
    );
  }
  if (activeBufferState.source !== STUDIO_WRITE_BUFFER_SOURCE) {
    return buildUnavailableWriteTarget(
      activeEntry.path,
      activeEntry.document_ref,
      "当前文稿不是来自 Studio 编辑器，暂不支持直接改写。",
    );
  }
  return {
    available: true,
    disabledReason: null,
    path: activeEntry.path,
    targetDocumentRef: activeEntry.document_ref,
  };
}

export function buildStudioWriteIntentNotice(
  writeTarget: StudioCurrentWriteTarget,
  enabled: boolean,
): string | null {
  if (enabled && writeTarget.available && writeTarget.path) {
    return `本轮只允许助手改写当前文稿：${writeTarget.path}`;
  }
  if (enabled) {
    return writeTarget.disabledReason ?? STUDIO_WRITE_UNAVAILABLE_MESSAGE;
  }
  return writeTarget.disabledReason;
}

export function resolveStudioWriteSendBlockReason(options: {
  enabled: boolean;
  writeTarget: StudioCurrentWriteTarget;
}) {
  if (!options.enabled) {
    return null;
  }
  if (options.writeTarget.available && options.writeTarget.targetDocumentRef) {
    return null;
  }
  return options.writeTarget.disabledReason ?? STUDIO_WRITE_UNAVAILABLE_MESSAGE;
}

export function resolveStudioWriteToggleDisabled(options: {
  enabled: boolean;
  writeTargetDisabledReason: string | null;
}) {
  return !options.enabled && Boolean(options.writeTargetDisabledReason);
}

export function resolveStudioRequestedWriteTargets(options: {
  enabled: boolean;
  writeTarget: StudioCurrentWriteTarget;
}) {
  const blockReason = resolveStudioWriteSendBlockReason(options);
  if (blockReason || !options.writeTarget.targetDocumentRef) {
    return null;
  }
  return [options.writeTarget.targetDocumentRef];
}

function buildUnavailableWriteTarget(
  path: string,
  targetDocumentRef: string | null,
  disabledReason: string,
): StudioCurrentWriteTarget {
  return {
    available: false,
    disabledReason,
    path,
    targetDocumentRef,
  };
}

function isNonEmptyString(value: string | null | undefined) {
  return typeof value === "string" && value.trim().length > 0;
}
