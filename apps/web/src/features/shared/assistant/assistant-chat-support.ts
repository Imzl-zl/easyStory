import { looksLikeRetiredModelMessage, normalizeModelProviderMessage } from "@/lib/api/error-copy";
import type { AssistantModelConfig } from "@/lib/api/types";
import { resolveAssistantMaxOutputTokens } from "@/features/shared/assistant/assistant-output-token-support";
import {
  buildAssistantReasoningPayload,
  resolveAssistantReasoningControl,
  resolveAssistantReasoningModelName,
  type AssistantReasoningDraftFields,
} from "@/features/shared/assistant/assistant-reasoning-support";

const TRUNCATED_REPLY_ERROR_PATTERN =
  /提前停止了这次回复|stop_reason=(length|max_tokens|max_output_tokens|MAX_TOKENS)/i;

type AssistantModelOverrideSettings = {
  maxOutputTokens: string;
  modelName: string;
  provider: string;
  reasoningEffort: string;
  thinkingBudget: string;
  thinkingLevel: string;
};

type AssistantReasoningSettings = Pick<
  AssistantModelOverrideSettings,
  "reasoningEffort" | "thinkingBudget" | "thinkingLevel"
>;

export function buildAssistantModelOverride(
  settings: AssistantModelOverrideSettings,
  options: {
    apiDialect?: string | null;
    defaultModelName?: string | null;
  } = {},
): AssistantModelConfig | undefined {
  const provider = normalizeAssistantProvider(settings.provider);
  const modelName = normalizeAssistantModelName(settings.modelName);
  const resolvedReasoningModelName = resolveAssistantReasoningModelName(
    modelName,
    options.defaultModelName,
  );
  if (!provider) {
    return undefined;
  }
  const reasoningPayload = buildAssistantReasoningPayload(
    buildIncubatorReasoningDraftFields(settings),
    resolveAssistantReasoningControl({
      apiDialect: options.apiDialect,
      modelName: resolvedReasoningModelName,
    }),
  );
  return {
    max_tokens: resolveAssistantMaxOutputTokens(settings.maxOutputTokens),
    provider,
    name: modelName || undefined,
    ...reasoningPayload,
  };
}

export function buildIncubatorReasoningDraftFields(
  settings: AssistantReasoningSettings,
): AssistantReasoningDraftFields {
  return {
    reasoningEffort: settings.reasoningEffort,
    thinkingBudget: settings.thinkingBudget,
    thinkingLevel: settings.thinkingLevel,
  };
}

export function resolveChatOutputModeLabel(streamOutput: boolean) {
  return streamOutput ? "边写边显示" : "生成后整体显示";
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

function normalizeAssistantProvider(provider: string | null | undefined) {
  return typeof provider === "string" ? provider.trim() : "";
}

function normalizeAssistantModelName(modelName: string | null | undefined) {
  return typeof modelName === "string" ? modelName.trim() : "";
}
