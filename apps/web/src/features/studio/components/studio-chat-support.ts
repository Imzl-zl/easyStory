import type { AssistantPreferences, AssistantTurnPayload } from "@/lib/api/types";
import { ASSISTANT_DEFAULT_CHAT_SKILL_ID } from "@/features/shared/assistant/assistant-defaults";
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

const STUDIO_CONTEXT_PREVIEW_MAX_LENGTH = 6000;
const STUDIO_CONTEXT_SELECTION_MAX_COUNT = 8;
const STUDIO_SYSTEM_MESSAGE = [
  "你是 easyStory 创作台里的小说协作助手。",
  "围绕当前文稿直接给可继续落笔的内容，不要转成后台配置或流程说明。",
  "优先帮用户补结构、顺段落、改措辞、续写场景、梳理冲突。",
  "如果上下文不完整，先基于已给文稿做最稳妥的建议，不要假装看过未提供的正文。",
  "回答保持中文，尽量贴近创作者工作流，少术语，少空话。",
].join("\n");

export const STUDIO_PENDING_REPLY_MESSAGE = "正在贴合当前文稿整理思路…";

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
  messages: StudioChatMessage[];
  projectId: string;
  settings: StudioChatSettings;
}): AssistantTurnPayload {
  return {
    messages: [
      { content: STUDIO_SYSTEM_MESSAGE, role: "system" as const },
      ...buildStudioPayloadMessages(options.messages),
    ],
    model: buildAssistantModelOverride(options.settings),
    project_id: options.projectId,
    skill_id: ASSISTANT_DEFAULT_CHAT_SKILL_ID,
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
  currentDocumentContent: string;
  currentDocumentPath: string | null;
  message: string;
  selectedContextPaths: string[];
}) {
  const contextNote = buildStudioContextNote(options);
  if (!contextNote) {
    return options.message;
  }
  return `${options.message}\n\n${contextNote}`;
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

function buildStudioContextNote(options: {
  attachments: StudioChatAttachment[];
  currentDocumentContent: string;
  currentDocumentPath: string | null;
  selectedContextPaths: string[];
}) {
  const sections: string[] = [];
  if (options.currentDocumentPath) {
    sections.push(`【当前文稿】\n${options.currentDocumentPath}`);
  }
  const trimmedContent = truncateStudioContextContent(options.currentDocumentContent);
  if (trimmedContent) {
    sections.push(`【当前文稿内容】\n${trimmedContent}`);
  }
  const contextPaths = resolveStudioContextPaths(options.currentDocumentPath, options.selectedContextPaths);
  if (contextPaths.length > 0) {
    sections.push(`【额外参考路径】\n${contextPaths.map((path) => `- ${path}`).join("\n")}`);
  }
  const attachmentContext = buildStudioAttachmentContext(options.attachments);
  if (attachmentContext) {
    sections.push(attachmentContext);
  }
  if (sections.length === 0) {
    return "";
  }
  return `请结合这份创作台上下文协作：\n\n${sections.join("\n\n")}`;
}

function buildStudioPayloadMessages(messages: StudioChatMessage[]) {
  return messages
    .filter((message) => message.status !== "pending" && message.status !== "error")
    .map((message) => ({
      content: message.requestContent ?? message.content,
      role: message.role,
    }));
}

function truncateStudioContextContent(content: string) {
  const trimmed = content.trim();
  if (!trimmed) {
    return "";
  }
  if (trimmed.length <= STUDIO_CONTEXT_PREVIEW_MAX_LENGTH) {
    return trimmed;
  }
  return `${trimmed.slice(0, STUDIO_CONTEXT_PREVIEW_MAX_LENGTH)}\n\n[内容过长，已截断到当前编辑区前半段]`;
}

function resolveStudioContextPaths(currentDocumentPath: string | null, selectedContextPaths: string[]) {
  const orderedPaths = [
    ...(currentDocumentPath ? [currentDocumentPath] : []),
    ...selectedContextPaths,
  ];
  return Array.from(new Set(orderedPaths)).slice(0, STUDIO_CONTEXT_SELECTION_MAX_COUNT);
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
