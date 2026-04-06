import type {
  AssistantActiveBufferState,
  AssistantDocumentContext,
  AssistantPreferences,
  ProjectDocumentCatalogEntry,
  AssistantTurnPayload,
} from "@/lib/api/types";
import {
  buildAssistantModelOverride,
  resolveFailedIncubatorReply,
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

export function buildStudioDocumentCatalogQueryKey(projectId: string) {
  return ["project-document-catalog", projectId] as const;
}

export type StudioChatMessage = {
  attachments?: StudioChatAttachmentMeta[];
  id: string;
  role: "user" | "assistant";
  content: string;
  rawMarkdown: string;
  requestContent?: string;
  status?: "pending" | "error";
};

export type StudioChatSettings = {
  maxOutputTokens: string;
  modelName: string;
  provider: string;
  streamOutput: boolean;
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
  };
}

export function appendStudioChatMessageDelta(
  messages: StudioChatMessage[],
  messageId: string,
  delta: string,
): StudioChatMessage[] {
  return messages.map((message) =>
    message.id === messageId
      ? {
        ...message,
        content: message.status === "pending" && message.content === STUDIO_PENDING_REPLY_MESSAGE
          ? delta
          : `${message.content}${delta}`,
        rawMarkdown: message.status === "pending" && message.rawMarkdown === STUDIO_PENDING_REPLY_MESSAGE
          ? delta
          : `${message.rawMarkdown}${delta}`,
      }
      : message,
  );
}

export function replaceStudioChatMessage(
  messages: StudioChatMessage[],
  messageId: string,
  nextMessage: StudioChatMessage,
): StudioChatMessage[] {
  return messages.map((message) => (message.id === messageId ? nextMessage : message));
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
  return resolveFailedIncubatorReply(content, errorMessage);
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
