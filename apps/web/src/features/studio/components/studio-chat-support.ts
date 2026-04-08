import type {
  AssistantActiveBufferState,
  AssistantDocumentContext,
  AssistantPreferences,
  ProjectDocumentCatalogEntry,
  AssistantTurnPayload,
} from "@/lib/api/types";
import {
  buildAssistantModelOverride,
  resolveFailedAssistantReply,
  resolveIncubatorAssistantReply,
} from "@/features/lobby/components/incubator-chat-support";
import {
  prefersBufferedOutput,
  type IncubatorCredentialOption,
} from "@/features/lobby/components/incubator-chat-credential-support";
import {
  resolveAssistantMaxOutputTokens,
} from "@/features/shared/assistant/assistant-output-token-support";
import {
  buildStudioAttachmentContext,
  type StudioChatAttachment,
  type StudioChatAttachmentMeta,
} from "./studio-chat-attachment-support";
import { normalizeStudioSkillId } from "./studio-chat-skill-support";

const STUDIO_CONTEXT_SELECTION_MAX_COUNT = 8;

export const STUDIO_PENDING_REPLY_MESSAGE = "正在贴合当前文稿整理思路…";
const STUDIO_INTERRUPTED_REPLY_MESSAGE = "这次回复中断了，你可以重新发送。";
const STUDIO_TOOL_PROGRESS_DETAIL_MAX_LENGTH = 40;
const STUDIO_TOOL_LABELS: Record<string, string> = {
  "project.list_documents": "整理文稿目录",
  "project.read_documents": "读取文稿",
  "project.search_documents": "检索文稿",
  "project.write_document": "写入文稿",
};

export function buildStudioDocumentCatalogQueryKey(projectId: string) {
  return ["project-document-catalog", projectId] as const;
}

export type StudioChatToolProgressTone = "running" | "success" | "danger" | "muted";

export type StudioChatToolProgressEntry = {
  detail?: string;
  label: string;
  statusLabel: string;
  toolCallId: string;
  tone: StudioChatToolProgressTone;
};

export type StudioChatToolProgressTerminalReason = "cancelled" | "interrupted";

export type StudioChatMessage = {
  attachments?: StudioChatAttachmentMeta[];
  id: string;
  role: "user" | "assistant";
  content: string;
  rawMarkdown: string;
  requestContent?: string;
  status?: "pending" | "error";
  toolProgress?: StudioChatToolProgressEntry[];
};

export type StudioChatSettings = {
  maxOutputTokens: string;
  modelName: string;
  provider: string;
  streamOutput: boolean;
};

export type StudioAssistantMessageActionState = {
  actionContent: string;
  copyLabel: string;
  documentMatchSource: string | null;
  showCopyAction: boolean;
  showDocumentActions: boolean;
};

export type StudioProviderOption = {
  description?: string;
  label: string;
  value: string;
};

export const INITIAL_STUDIO_CHAT_SETTINGS: StudioChatSettings = {
  maxOutputTokens: "",
  modelName: "",
  provider: "",
  streamOutput: true,
};

export function createStudioChatMessage(
  role: StudioChatMessage["role"],
  content: string,
  options: {
    attachments?: StudioChatAttachmentMeta[];
    rawMarkdown?: string;
    requestContent?: string;
    status?: StudioChatMessage["status"];
    toolProgress?: StudioChatMessage["toolProgress"];
  } = {},
): StudioChatMessage {
  return {
    attachments: options.attachments,
    content,
    id: `${role}-${Math.random().toString(36).slice(2, 10)}`,
    rawMarkdown: options.rawMarkdown ?? content,
    requestContent: options.requestContent,
    role,
    status: options.status,
    toolProgress: options.toolProgress,
  };
}

export function appendStudioChatMessageDelta(
  messages: StudioChatMessage[],
  messageId: string,
  delta: string,
): StudioChatMessage[] {
  return mapStudioChatMessage(messages, messageId, (message) => ({
    ...message,
    content: message.status === "pending" && message.content === STUDIO_PENDING_REPLY_MESSAGE
      ? delta
      : `${message.content}${delta}`,
    rawMarkdown: message.status === "pending" && message.rawMarkdown === STUDIO_PENDING_REPLY_MESSAGE
      ? delta
      : `${message.rawMarkdown}${delta}`,
  }));
}

export function replaceStudioChatMessage(
  messages: StudioChatMessage[],
  messageId: string,
  nextMessage: StudioChatMessage,
): StudioChatMessage[] {
  return mapStudioChatMessage(messages, messageId, () => nextMessage);
}

export function applyStudioChatToolCallStart(
  messages: StudioChatMessage[],
  messageId: string,
  payload: {
    target_summary?: unknown;
    tool_call_id: string;
    tool_name: string;
  },
): StudioChatMessage[] {
  return mapStudioChatMessage(messages, messageId, (message) => ({
    ...message,
    toolProgress: upsertStudioToolProgressEntry(message.toolProgress, {
      detail: resolveStudioToolStartDetail(payload.target_summary),
      label: resolveStudioToolLabel(payload.tool_name),
      statusLabel: "处理中",
      toolCallId: payload.tool_call_id,
      tone: "running",
    }),
  }));
}

export function applyStudioChatToolCallResult(
  messages: StudioChatMessage[],
  messageId: string,
  payload: {
    error?: unknown;
    result_summary?: unknown;
    status: string;
    tool_call_id: string;
    tool_name: string;
  },
): StudioChatMessage[] {
  const nextStatus = resolveStudioToolResultStatus(payload.status);
  return mapStudioChatMessage(messages, messageId, (message) => ({
    ...message,
    toolProgress: upsertStudioToolProgressEntry(message.toolProgress, {
      detail: resolveStudioToolResultDetail(payload.result_summary, payload.error),
      label: resolveStudioToolLabel(payload.tool_name),
      statusLabel: nextStatus.statusLabel,
      toolCallId: payload.tool_call_id,
      tone: nextStatus.tone,
    }),
  }));
}

export function finalizeStudioChatToolProgress(
  entries: StudioChatToolProgressEntry[] | undefined,
  reason: StudioChatToolProgressTerminalReason,
) {
  if (!entries?.length) {
    return entries;
  }
  const statusLabel = reason === "cancelled" ? "已停止" : "已中断";
  let didChange = false;
  const nextEntries = entries.map((entry) => {
    if (entry.tone !== "running") {
      return entry;
    }
    didChange = true;
    return {
      ...entry,
      statusLabel,
      tone: "muted" as const,
    };
  });
  return didChange ? nextEntries : entries;
}

export function buildStudioAssistantTurnPayload(options: {
  activeBufferState?: AssistantActiveBufferState | null;
  conversationId: string;
  currentDocumentPath: string | null;
  documentCatalogEntries?: ProjectDocumentCatalogEntry[] | null;
  latestCompletedRunId: string | null;
  messages: StudioChatMessage[];
  projectId: string;
  requestedWriteTargets?: string[] | null;
  selectedContextPaths: string[];
  settings: StudioChatSettings;
  skillId?: string | null;
}): AssistantTurnPayload {
  const skillId = normalizeStudioSkillId(options.skillId);
  const documentContext = buildStudioDocumentContext(
    options.activeBufferState,
    options.currentDocumentPath,
    options.documentCatalogEntries,
    options.selectedContextPaths,
  );
  const currentUserMessage = options.messages[options.messages.length - 1];
  if (!currentUserMessage || currentUserMessage.role !== "user") {
    throw new Error("Studio assistant turn payload requires the latest user message.");
  }
  const requestedWriteTargets = options.requestedWriteTargets?.length
    ? options.requestedWriteTargets
    : null;
  return {
    conversation_id: options.conversationId,
    client_turn_id: currentUserMessage.id,
    messages: buildStudioPayloadMessages(options.messages),
    model: buildAssistantModelOverride(options.settings),
    ...(documentContext ? { document_context: documentContext } : {}),
    ...(options.latestCompletedRunId
      ? {
        continuation_anchor: {
          previous_run_id: options.latestCompletedRunId,
        },
      }
      : {}),
    project_id: options.projectId,
    requested_write_scope: requestedWriteTargets ? "turn" : "disabled",
    ...(requestedWriteTargets ? { requested_write_targets: requestedWriteTargets } : {}),
    ...(skillId ? { skill_id: skillId } : {}),
  };
}

export function buildStudioProviderOptions(
  credentialOptions: IncubatorCredentialOption[],
): StudioProviderOption[] {
  return credentialOptions.map((option) => ({
    description: option.defaultModel ? `默认模型：${option.defaultModel}` : "当前连接未设置默认模型",
    label: option.displayLabel,
    value: option.provider,
  }));
}

export function buildNextStudioChatSettingsForProvider(
  credentialOptions: IncubatorCredentialOption[],
  current: StudioChatSettings,
  provider: string,
): StudioChatSettings {
  const currentOption = credentialOptions.find((item) => item.provider === current.provider) ?? null;
  const nextOption = credentialOptions.find((item) => item.provider === provider) ?? null;
  return {
    ...current,
    maxOutputTokens: resolveNextStudioTokenDraft(current.maxOutputTokens, currentOption, nextOption),
    modelName: nextOption?.defaultModel ?? "",
    provider,
    streamOutput: prefersBufferedOutput(nextOption) ? false : current.streamOutput,
  };
}

export function mergeStudioAssistantPreferences(
  projectPreferences?: AssistantPreferences,
  userPreferences?: AssistantPreferences,
): AssistantPreferences | undefined {
  if (!projectPreferences && !userPreferences) {
    return undefined;
  }
  return {
    default_max_output_tokens:
      projectPreferences?.default_max_output_tokens ?? userPreferences?.default_max_output_tokens ?? null,
    default_model_name:
      projectPreferences?.default_model_name ?? userPreferences?.default_model_name ?? null,
    default_provider:
      projectPreferences?.default_provider ?? userPreferences?.default_provider ?? null,
  };
}

export function buildStudioCredentialSettingsHref(projectId: string) {
  return `/workspace/lobby/settings?tab=credentials&scope=project&project=${projectId}&sub=list`;
}

export function normalizeStudioAssistantReply(content: string) {
  return resolveIncubatorAssistantReply(content);
}

export function resolveStudioFailedReply(content: string, errorMessage: string) {
  return resolveFailedAssistantReply(content, errorMessage, {
    interruptedMessage: STUDIO_INTERRUPTED_REPLY_MESSAGE,
    pendingMessage: STUDIO_PENDING_REPLY_MESSAGE,
  });
}

export function resolveStudioAssistantMessageActionState(
  message: Pick<StudioChatMessage, "content" | "rawMarkdown" | "role" | "status">,
): StudioAssistantMessageActionState {
  if (message.role !== "assistant" || message.status === "pending") {
    return {
      actionContent: message.content,
      copyLabel: "复制 Markdown",
      documentMatchSource: null,
      showCopyAction: false,
      showDocumentActions: false,
    };
  }
  if (message.status === "error") {
    return {
      actionContent: message.content,
      copyLabel: "复制内容",
      documentMatchSource: null,
      showCopyAction: true,
      showDocumentActions: false,
    };
  }
  const markdownSource = message.rawMarkdown || message.content;
  return {
    actionContent: markdownSource,
    copyLabel: "复制 Markdown",
    documentMatchSource: markdownSource,
    showCopyAction: true,
    showDocumentActions: true,
  };
}

export function buildStudioUserRequestContent(options: {
  attachments: StudioChatAttachment[];
  message: string;
}) {
  const attachmentContext = buildStudioAttachmentContext(options.attachments);
  if (!attachmentContext) {
    return options.message;
  }
  return `${options.message}\n\n请结合我附带的文件继续：\n\n${attachmentContext}`;
}

function mapStudioChatMessage(
  messages: StudioChatMessage[],
  messageId: string,
  updater: (message: StudioChatMessage) => StudioChatMessage,
) {
  let didChange = false;
  const nextMessages = messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    const nextMessage = updater(message);
    didChange = didChange || nextMessage !== message;
    return nextMessage;
  });
  return didChange ? nextMessages : messages;
}

function upsertStudioToolProgressEntry(
  entries: StudioChatToolProgressEntry[] | undefined,
  nextEntry: StudioChatToolProgressEntry,
) {
  const currentEntries = entries ?? [];
  const currentIndex = currentEntries.findIndex((item) => item.toolCallId === nextEntry.toolCallId);
  if (currentIndex < 0) {
    return [...currentEntries, nextEntry];
  }
  return currentEntries.map((item, index) =>
    index === currentIndex
      ? {
        ...item,
        detail: nextEntry.detail ?? item.detail,
        label: nextEntry.label,
        statusLabel: nextEntry.statusLabel,
        tone: nextEntry.tone,
      }
      : item);
}

function resolveStudioToolLabel(toolName: string) {
  return STUDIO_TOOL_LABELS[toolName] ?? "调用工具";
}

function resolveStudioToolStartDetail(summary: unknown) {
  const record = readStudioToolRecord(summary);
  if (!record) {
    return undefined;
  }
  const path = readStudioToolString(record.path);
  if (path) {
    return path;
  }
  const query = readStudioToolString(record.query);
  if (query) {
    return `检索：${truncateStudioToolDetail(query)}`;
  }
  const paths = readStudioToolStringArray(record.paths);
  if (paths.length === 1) {
    return paths[0];
  }
  const documentCount = readStudioToolCount(record.document_count) ?? (paths.length > 1 ? paths.length : null);
  if (documentCount) {
    return `${documentCount} 篇文稿`;
  }
  const pathPrefix = readStudioToolString(record.path_prefix);
  if (pathPrefix) {
    return pathPrefix;
  }
  const limit = readStudioToolCount(record.limit);
  if (limit) {
    return `最多 ${limit} 篇`;
  }
  return undefined;
}

function resolveStudioToolResultDetail(summary: unknown, error: unknown) {
  const summaryRecord = readStudioToolRecord(summary);
  const summaryMessage = readStudioToolString(summaryRecord?.message);
  if (summaryMessage) {
    return truncateStudioToolDetail(summaryMessage);
  }
  const documentCount = readStudioToolCount(summaryRecord?.document_count);
  if (documentCount) {
    return `${documentCount} 篇文稿`;
  }
  const paths = readStudioToolStringArray(summaryRecord?.paths);
  if (paths.length === 1) {
    return paths[0];
  }
  if (paths.length > 1) {
    return `${paths.length} 篇文稿`;
  }
  const resourceCount = readStudioToolCount(summaryRecord?.resource_count);
  if (resourceCount) {
    return `${resourceCount} 项资源`;
  }
  const contentItemCount = readStudioToolCount(summaryRecord?.content_item_count);
  if (contentItemCount) {
    return `${contentItemCount} 项内容`;
  }
  const errorMessage = readStudioToolString(readStudioToolRecord(error)?.message);
  return errorMessage ? truncateStudioToolDetail(errorMessage) : undefined;
}

function resolveStudioToolResultStatus(status: string) {
  switch (status.trim()) {
    case "cancelled":
      return { statusLabel: "已停止", tone: "muted" as const };
    case "committed":
      return { statusLabel: "已写入", tone: "success" as const };
    case "failed":
    case "rejected":
      return { statusLabel: "失败", tone: "danger" as const };
    case "completed":
      return { statusLabel: "已完成", tone: "success" as const };
    default:
      return { statusLabel: "已返回", tone: "success" as const };
  }
}

function truncateStudioToolDetail(value: string) {
  return value.length > STUDIO_TOOL_PROGRESS_DETAIL_MAX_LENGTH
    ? `${value.slice(0, STUDIO_TOOL_PROGRESS_DETAIL_MAX_LENGTH)}…`
    : value;
}

function readStudioToolRecord(value: unknown) {
  return typeof value === "object" && value !== null ? value as Record<string, unknown> : null;
}

function readStudioToolString(value: unknown) {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function readStudioToolStringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function readStudioToolCount(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? Math.trunc(value) : null;
}

function buildStudioDocumentContext(
  activeBufferState: AssistantActiveBufferState | null | undefined,
  currentDocumentPath: string | null,
  documentCatalogEntries: ProjectDocumentCatalogEntry[] | null | undefined,
  selectedContextPaths: string[],
): AssistantDocumentContext | null {
  const normalizedSelectedPaths = resolveStudioSelectedContextPaths(
    currentDocumentPath,
    selectedContextPaths,
  );
  if (!currentDocumentPath && normalizedSelectedPaths.length === 0) {
    return null;
  }
  const catalogEntries = requireStudioDocumentCatalogEntries(documentCatalogEntries);
  const catalogEntriesByPath = buildStudioDocumentCatalogEntryMap(catalogEntries);
  const activeEntry = currentDocumentPath
    ? requireStudioDocumentCatalogEntry(catalogEntriesByPath, currentDocumentPath)
    : null;
  const selectedEntries = normalizedSelectedPaths.map((path) =>
    requireStudioDocumentCatalogEntry(catalogEntriesByPath, path));
  return {
    ...(currentDocumentPath
      ? {
        active_path: currentDocumentPath,
        active_document_ref: activeEntry?.document_ref,
        active_binding_version: activeEntry?.binding_version,
      }
      : {}),
    ...(activeBufferState ? { active_buffer_state: activeBufferState } : {}),
    ...(normalizedSelectedPaths.length > 0
      ? {
        selected_paths: normalizedSelectedPaths,
        selected_document_refs: selectedEntries.map((entry) => entry.document_ref),
      }
      : {}),
    catalog_version: catalogEntries[0].catalog_version,
  };
}

function buildStudioDocumentCatalogEntryMap(
  documentCatalogEntries: ProjectDocumentCatalogEntry[],
) {
  return new Map(documentCatalogEntries.map((entry) => [entry.path, entry]));
}

function requireStudioDocumentCatalogEntries(
  documentCatalogEntries: ProjectDocumentCatalogEntry[] | null | undefined,
) {
  if (!documentCatalogEntries || documentCatalogEntries.length === 0) {
    throw new Error("当前文稿目录快照尚未就绪，请稍后重试。");
  }
  return documentCatalogEntries;
}

function requireStudioDocumentCatalogEntry(
  catalogEntriesByPath: Map<string, ProjectDocumentCatalogEntry>,
  path: string,
) {
  const entry = catalogEntriesByPath.get(path);
  if (entry) {
    return entry;
  }
  throw new Error(`当前文稿目录快照已过期，请刷新后重试：${path}`);
}

function buildStudioPayloadMessages(messages: StudioChatMessage[]) {
  return messages
    .filter((message) => message.status !== "pending" && message.status !== "error")
    .map((message) => ({
      content: message.requestContent ?? message.content,
      role: message.role,
    }));
}

function resolveStudioSelectedContextPaths(
  currentDocumentPath: string | null,
  selectedContextPaths: string[],
) {
  return resolveStudioContextPaths(
    null,
    selectedContextPaths.filter((path) => path !== currentDocumentPath),
  );
}

function resolveStudioContextPaths(currentDocumentPath: string | null, selectedContextPaths: string[]) {
  const orderedPaths = [
    ...(currentDocumentPath ? [currentDocumentPath] : []),
    ...selectedContextPaths,
  ];
  return Array.from(new Set(orderedPaths)).slice(0, STUDIO_CONTEXT_SELECTION_MAX_COUNT);
}

export function resolveStudioModelButtonLabel(options: {
  modelName: string;
  selectedCredential: IncubatorCredentialOption | null;
}) {
  const customModelName = options.modelName.trim();
  if (customModelName) {
    return customModelName;
  }
  const defaultModel = options.selectedCredential?.defaultModel?.trim() ?? "";
  return defaultModel || "选择模型";
}

function resolveNextStudioTokenDraft(
  currentValue: string,
  currentOption: IncubatorCredentialOption | null,
  nextOption: IncubatorCredentialOption | null,
) {
  const normalizedCurrentValue = currentValue.trim();
  if (!normalizedCurrentValue) {
    return resolveStudioTokenDraft(nextOption);
  }
  if (normalizedCurrentValue !== resolveStudioTokenDraft(currentOption)) {
    return currentValue;
  }
  return resolveStudioTokenDraft(nextOption);
}

function resolveStudioTokenDraft(option: IncubatorCredentialOption | null) {
  return String(option?.defaultMaxOutputTokens ?? resolveAssistantMaxOutputTokens(""));
}
