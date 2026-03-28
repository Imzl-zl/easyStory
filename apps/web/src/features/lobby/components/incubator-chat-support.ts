import { normalizeModelProviderMessage, looksLikeRetiredModelMessage } from "@/lib/api/error-copy";
import type { AssistantMessage, AssistantModelConfig, ProjectSetting } from "@/lib/api/types";

export const INCUBATOR_DEFAULT_PROVIDER = "";
export const INCUBATOR_DEFAULT_MODEL_NAME = "";
export const INCUBATOR_CHAT_SKILL_ID = "skill.assistant.general_chat";
export const INCUBATOR_INPUT_MAX_LENGTH = 4000;
export const INCUBATOR_DEFAULT_PROJECT_NAME = "未命名新故事";
export const INCUBATOR_PENDING_REPLY_MESSAGE = "正在整理故事方向…";
export const INCUBATOR_INTERRUPTED_REPLY_MESSAGE = "这次回复中断了，你可以重新发送。";

export const INCUBATOR_PROMPT_SUGGESTIONS = [
  "我完全不知道写什么，先给我 3 个适合新手的故事方向。",
  "最近什么类型的故事更容易让人读下去？",
  "我想写轻松一点的成长故事，帮我定个方向。",
  "给我 3 个开局有钩子的小说点子。",
] as const;

export type IncubatorChatMessage = AssistantMessage & {
  id: string;
  hidden?: boolean;
  status?: "pending" | "error";
};

export type IncubatorChatSettings = {
  allowSystemCredentialPool: boolean;
  modelName: string;
  provider: string;
  streamOutput: boolean;
};

export const INITIAL_INCUBATOR_CHAT_SETTINGS: IncubatorChatSettings = {
  allowSystemCredentialPool: false,
  modelName: INCUBATOR_DEFAULT_MODEL_NAME,
  provider: INCUBATOR_DEFAULT_PROVIDER,
  streamOutput: true,
};

const INCUBATOR_SYSTEM_MESSAGE = [
  "你是 easyStory 的小说创作启动助手。",
  "用户是纯新手时，不要要求他先给出完整设定。",
  "优先做三件事：帮助找方向、给出可选方案、一次只追问一个关键问题。",
  "如果用户说不知道写什么，先给 2 到 3 个具体故事方向，每个方向都要有题材、主角钩子、核心冲突。",
  "回答保持中文、直接、有人味，避免术语堆砌。",
  "不要把回复写成表单或大纲问卷。",
  "当信息已经足够整理项目草稿时，可以提醒用户已经可以整理草稿并创建项目。",
].join("\n");

const INCUBATOR_WELCOME_MESSAGE = [
  "你现在想到的一点点画面、角色念头，或者一句模糊感觉，都可以先发给我。",
  "如果你还没方向，我也可以先给你几个更容易开写的故事点子。",
].join("\n");

export function createIncubatorInitialMessages(): IncubatorChatMessage[] {
  return [
    createIncubatorMessage("system", INCUBATOR_SYSTEM_MESSAGE, { hidden: true }),
    createIncubatorMessage("assistant", INCUBATOR_WELCOME_MESSAGE),
  ];
}

export function createIncubatorMessage(
  role: IncubatorChatMessage["role"],
  content: string,
  options: Pick<IncubatorChatMessage, "hidden" | "status"> = {},
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

export function buildAssistantTurnMessages(
  messages: IncubatorChatMessage[],
): AssistantMessage[] {
  return messages
    .filter((message) => message.status !== "pending" && message.status !== "error")
    .map(({ content, role }) => ({ content, role }));
}

export function buildIncubatorConversationText(
  messages: IncubatorChatMessage[],
): string {
  const firstUserIndex = messages.findIndex((message) => message.role === "user");
  if (firstUserIndex === -1) {
    return "";
  }
  return messages
    .slice(firstUserIndex)
    .filter((message) => message.status !== "pending" && message.status !== "error")
    .map((message) => `${resolveMessageRoleLabel(message.role)}：${message.content}`)
    .join("\n\n");
}

export function buildIncubatorConversationFingerprint(
  messages: IncubatorChatMessage[],
  settings: Pick<IncubatorChatSettings, "modelName" | "provider">,
): string {
  return JSON.stringify({
    conversationText: buildIncubatorConversationText(messages),
    modelName: resolveIncubatorModelName(settings.modelName),
    provider: resolveIncubatorProvider(settings.provider),
  });
}

export function buildAssistantModelOverride(
  settings: Pick<IncubatorChatSettings, "modelName" | "provider">,
): AssistantModelConfig | undefined {
  const provider = resolveIncubatorProvider(settings.provider);
  const modelName = resolveIncubatorModelName(settings.modelName);
  if (!provider) {
    return undefined;
  }
  return {
    provider,
    name: modelName || undefined,
  };
}

export function resolveChatOutputModeLabel(streamOutput: boolean) {
  return streamOutput ? "边写边显示" : "生成后整体显示";
}

export function resolveInterruptedIncubatorReply(content: string) {
  const trimmed = content.trim();
  if (!trimmed || trimmed === INCUBATOR_PENDING_REPLY_MESSAGE) {
    return null;
  }
  return `${trimmed}\n\n${INCUBATOR_INTERRUPTED_REPLY_MESSAGE}`;
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
  if (role === "system") {
    return "系统";
  }
  return "用户";
}

export function resolveIncubatorProvider(provider: string) {
  return provider.trim();
}

export function resolveIncubatorModelName(modelName: string) {
  return modelName.trim();
}

function normalizeText(value: string | undefined) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
