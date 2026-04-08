import { normalizeModelProviderMessage, looksLikeRetiredModelMessage } from "@/lib/api/error-copy";
import type {
  AssistantHookResult,
  AssistantMessage,
  AssistantModelConfig,
  ProjectSetting,
} from "@/lib/api/types";
import {
  resolveAssistantMaxOutputTokens,
} from "@/features/shared/assistant/assistant-output-token-support";

export const INCUBATOR_DEFAULT_PROVIDER = "";
export const INCUBATOR_DEFAULT_MODEL_NAME = "";
export const INCUBATOR_NO_SKILL_ID = "";
export const INCUBATOR_NO_SKILL_LABEL = "不额外套用 Skill";
export const INCUBATOR_NO_AGENT_ID = "";
export const INCUBATOR_NO_AGENT_LABEL = "直接聊天";
export const INCUBATOR_UNAVAILABLE_SKILL_LABEL_PREFIX = "当前 Skill 不可用";
export const INCUBATOR_UNAVAILABLE_AGENT_LABEL_PREFIX = "当前 Agent 不可用";
export const INCUBATOR_INPUT_MAX_LENGTH = 4000;
export const INCUBATOR_DEFAULT_PROJECT_NAME = "未命名新故事";
export const INCUBATOR_PENDING_REPLY_MESSAGE = "正在整理故事方向…";
export const INCUBATOR_INTERRUPTED_REPLY_MESSAGE = "这次回复中断了，你可以重新发送。";
const TRUNCATED_REPLY_ERROR_PATTERN = /提前停止了这次回复|stop_reason=(length|max_tokens|max_output_tokens|MAX_TOKENS)/i;

export const INCUBATOR_PROMPT_SUGGESTIONS = [
  "我完全不知道写什么，先给我 3 个适合新手的故事方向。",
  "最近什么类型的故事更容易让人读下去？",
  "我想写轻松一点的成长故事，帮我定个方向。",
  "给我 3 个开局有钩子的小说点子。",
] as const;

export type IncubatorChatMessage = AssistantMessage & {
  id: string;
  hookResults?: AssistantHookResult[];
  hidden?: boolean;
  status?: "pending" | "error";
};

export type IncubatorChatSettings = {
  agentId: string;
  allowSystemCredentialPool: boolean;
  hookIds: string[];
  maxOutputTokens: string;
  modelName: string;
  provider: string;
  skillId: string;
  streamOutput: boolean;
};

export const INITIAL_INCUBATOR_CHAT_SETTINGS: IncubatorChatSettings = {
  agentId: INCUBATOR_NO_AGENT_ID,
  allowSystemCredentialPool: false,
  hookIds: [],
  maxOutputTokens: "",
  modelName: INCUBATOR_DEFAULT_MODEL_NAME,
  provider: INCUBATOR_DEFAULT_PROVIDER,
  skillId: INCUBATOR_NO_SKILL_ID,
  streamOutput: true,
};

const INCUBATOR_WELCOME_MESSAGE = [
  "你现在想到的一点点画面、角色念头，或者一句模糊感觉，都可以先发给我。",
  "如果你还没方向，我也可以先给你几个更容易开写的故事点子。",
].join("\n");

export function createIncubatorInitialMessages(): IncubatorChatMessage[] {
  return [createIncubatorMessage("assistant", INCUBATOR_WELCOME_MESSAGE)];
}

export function createIncubatorMessage(
  role: IncubatorChatMessage["role"],
  content: string,
  options: Pick<IncubatorChatMessage, "hidden" | "hookResults" | "status"> = {},
): IncubatorChatMessage {
  return {
    id: `${role}-${Math.random().toString(36).slice(2, 10)}`,
    role,
    content,
    ...options,
  };
}

export function replaceIncubatorMessage(
  messages: IncubatorChatMessage[],
  messageId: string,
  nextMessage: IncubatorChatMessage,
): IncubatorChatMessage[] {
  return messages.map((message) => (message.id === messageId ? nextMessage : message));
}

export function appendIncubatorMessageDelta(
  messages: IncubatorChatMessage[],
  messageId: string,
  delta: string,
): IncubatorChatMessage[] {
  return messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    const nextContent = message.status === "pending" && message.content === INCUBATOR_PENDING_REPLY_MESSAGE
      ? delta
      : `${message.content}${delta}`;
    return { ...message, content: nextContent };
  });
}

export function resolveIncubatorAssistantReply(content: string) {
  const trimmed = content.trim();
  if (!looksLikeRetiredModelMessage(trimmed)) {
    return { content, status: undefined };
  }
  return {
    content: `${normalizeModelProviderMessage(trimmed)} 你可以先到“模型连接”里修改默认模型，再回来继续聊天。`,
    status: "error" as const,
  };
}

export function isIncubatorConversationRole(role: string): role is AssistantMessage["role"] {
  return role === "assistant" || role === "user";
}

export function sanitizeIncubatorConversationMessages(
  messages: IncubatorChatMessage[],
): IncubatorChatMessage[] {
  return messages.filter((message) => isIncubatorConversationRole(message.role));
}

export function buildAssistantTurnMessages(
  messages: IncubatorChatMessage[],
): AssistantMessage[] {
  return sanitizeIncubatorConversationMessages(messages)
    .filter((message) => message.status !== "pending" && message.status !== "error")
    .map(({ content, role }) => ({ content, role }));
}

export function buildIncubatorConversationText(
  messages: IncubatorChatMessage[],
): string {
  const visibleMessages = sanitizeIncubatorConversationMessages(messages)
    .filter((message) => message.status !== "pending" && message.status !== "error");
  const firstUserIndex = visibleMessages.findIndex((message) => message.role === "user");
  if (firstUserIndex === -1) {
    return "";
  }
  return visibleMessages
    .slice(firstUserIndex)
    .map((message) => `${resolveMessageRoleLabel(message.role)}：${message.content}`)
    .join("\n\n");
}

export function buildIncubatorConversationFingerprint(
  messages: IncubatorChatMessage[],
  settings: Pick<IncubatorChatSettings, "agentId" | "hookIds" | "modelName" | "provider" | "skillId">,
): string {
  return JSON.stringify({
    agentId: resolveIncubatorAgentId(settings.agentId),
    conversationText: buildIncubatorConversationText(messages),
    hookIds: resolveIncubatorHookIds(settings.hookIds),
    modelName: resolveIncubatorModelName(settings.modelName),
    provider: resolveIncubatorProvider(settings.provider),
    skillId: resolveIncubatorSkillId(settings.skillId),
  });
}

export function buildAssistantModelOverride(
  settings: Pick<IncubatorChatSettings, "maxOutputTokens" | "modelName" | "provider">,
): AssistantModelConfig | undefined {
  const provider = resolveIncubatorProvider(settings.provider);
  const modelName = resolveIncubatorModelName(settings.modelName);
  if (!provider) {
    return undefined;
  }
  return {
    max_tokens: resolveAssistantMaxOutputTokens(settings.maxOutputTokens),
    provider,
    name: modelName || undefined,
  };
}

export function resolveChatOutputModeLabel(streamOutput: boolean) {
  return streamOutput ? "边写边显示" : "生成后整体显示";
}

export function resolveInterruptedIncubatorReply(content: string) {
  return resolveInterruptedAssistantReply(content, {
    interruptedMessage: INCUBATOR_INTERRUPTED_REPLY_MESSAGE,
    pendingMessage: INCUBATOR_PENDING_REPLY_MESSAGE,
  });
}

export function resolveFailedIncubatorReply(
  content: string,
  errorMessage: string,
) {
  return resolveFailedAssistantReply(content, errorMessage, {
    interruptedMessage: INCUBATOR_INTERRUPTED_REPLY_MESSAGE,
    pendingMessage: INCUBATOR_PENDING_REPLY_MESSAGE,
  });
}

export function resolveFailedAssistantReply(
  content: string,
  errorMessage: string,
  options: {
    interruptedMessage: string;
    pendingMessage: string;
  },
) {
  const trimmedContent = content.trim();
  const trimmedError = errorMessage.trim();
  if (!trimmedContent || trimmedContent === options.pendingMessage) {
    return trimmedError || null;
  }
  if (TRUNCATED_REPLY_ERROR_PATTERN.test(trimmedError)) {
    return `${trimmedContent}\n\n${trimmedError}`;
  }
  return resolveInterruptedAssistantReply(trimmedContent, options) ?? (trimmedError || null);
}

function resolveInterruptedAssistantReply(
  content: string,
  options: {
    interruptedMessage: string;
    pendingMessage: string;
  },
) {
  const trimmed = content.trim();
  if (!trimmed || trimmed === options.pendingMessage) {
    return null;
  }
  return `${trimmed}\n\n${options.interruptedMessage}`;
}

export function shouldShowPromptSuggestions(hasUserMessage: boolean) {
  return !hasUserMessage;
}

export function shouldSubmitIncubatorComposer(options: {
  isComposing: boolean;
  key: string;
  shiftKey: boolean;
}) {
  if (options.isComposing) {
    return false;
  }
  if (options.key !== "Enter") {
    return false;
  }
  return !options.shiftKey;
}

export function buildSuggestedProjectName(setting: ProjectSetting): string {
  const protagonistName = normalizeText(setting.protagonist?.name);
  const protagonistIdentity = normalizeText(setting.protagonist?.identity);
  const genre = normalizeText(setting.sub_genre) ?? normalizeText(setting.genre);

  if (protagonistName && genre) {
    return `${protagonistName}的${genre}故事`;
  }
  if (protagonistIdentity && genre) {
    return `${protagonistIdentity}的${genre}故事`;
  }
  if (protagonistName) {
    return `关于${protagonistName}的故事`;
  }
  if (protagonistIdentity) {
    return `${protagonistIdentity}成长记`;
  }
  if (genre) {
    return `${genre}新故事`;
  }
  return INCUBATOR_DEFAULT_PROJECT_NAME;
}

function resolveMessageRoleLabel(role: AssistantMessage["role"]) {
  if (role === "assistant") {
    return "助手";
  }
  return "用户";
}

export function resolveIncubatorProvider(provider: string | null | undefined) {
  return typeof provider === "string" ? provider.trim() : "";
}

export function resolveIncubatorModelName(modelName: string | null | undefined) {
  return typeof modelName === "string" ? modelName.trim() : "";
}

export function resolveIncubatorSkillId(skillId: string | null | undefined) {
  return typeof skillId === "string" ? skillId.trim() : "";
}

export function resolveIncubatorSkillLabel(
  options: ReadonlyArray<{ label: string; value: string }>,
  skillId: string | null | undefined,
) {
  const resolvedSkillId = resolveIncubatorSkillId(skillId);
  const matchedOption = options.find((option) => option.value === resolvedSkillId);
  if (matchedOption) {
    return matchedOption.label;
  }
  return resolvedSkillId === INCUBATOR_NO_SKILL_ID
    ? INCUBATOR_NO_SKILL_LABEL
    : `${INCUBATOR_UNAVAILABLE_SKILL_LABEL_PREFIX}：${resolvedSkillId}`;
}

export function resolveIncubatorAgentId(agentId: string | null | undefined) {
  return typeof agentId === "string" ? agentId.trim() : "";
}

export function resolveIncubatorHookIds(hookIds: string[] | null | undefined) {
  if (!Array.isArray(hookIds)) {
    return [];
  }
  return Array.from(new Set(
    hookIds
      .map((item) => (typeof item === "string" ? item.trim() : ""))
      .filter(Boolean),
  )).sort();
}

export function toggleIncubatorHookId(
  currentHookIds: string[],
  hookId: string,
) {
  const normalizedHookId = hookId.trim();
  if (!normalizedHookId) {
    return resolveIncubatorHookIds(currentHookIds);
  }
  const nextHookIds = currentHookIds.includes(normalizedHookId)
    ? currentHookIds.filter((item) => item !== normalizedHookId)
    : [...currentHookIds, normalizedHookId];
  return resolveIncubatorHookIds(nextHookIds);
}

export function resolveIncubatorAgentLabel(
  options: ReadonlyArray<{ label: string; value: string }>,
  agentId: string | null | undefined,
) {
  const resolvedAgentId = resolveIncubatorAgentId(agentId);
  if (!resolvedAgentId) {
    return INCUBATOR_NO_AGENT_LABEL;
  }
  const matchedOption = options.find((option) => option.value === resolvedAgentId);
  return matchedOption
    ? matchedOption.label
    : `${INCUBATOR_UNAVAILABLE_AGENT_LABEL_PREFIX}：${resolvedAgentId}`;
}

function normalizeText(value: string | undefined) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
