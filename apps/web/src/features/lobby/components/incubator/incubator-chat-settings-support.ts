"use client";

import {
  resolveAssistantMaxOutputTokens,
  sanitizeAssistantOutputTokenInput,
} from "@/features/shared/assistant/assistant-output-token-support";
import {
  buildIncubatorReasoningDraftFields,
  resolveChatOutputModeLabel,
} from "@/features/shared/assistant/assistant-chat-support";
import {
  describeAssistantReasoningSelection,
  normalizeAssistantReasoningDraft,
  resolveAssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";

import { prefersBufferedOutput } from "@/features/shared/assistant/assistant-credential-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";

export function updateIncubatorChatSetting<K extends keyof IncubatorChatModel["settings"]>(
  model: IncubatorChatModel,
  field: K,
  value: IncubatorChatModel["settings"][K],
) {
  model.setSettings((current) => ({ ...current, [field]: value }));
}

export function buildChatSettingsSummaryItems(model: IncubatorChatModel) {
  return buildChatSettingsSummaryItemsWithSkill(model, null);
}

export function buildChatSettingsSummaryItemsWithSkill(
  model: IncubatorChatModel,
  skillLabel: string | null,
) {
  if (model.credentialState === "loading") {
    return ["正在读取模型连接"];
  }
  if (model.credentialState === "error") {
    return ["模型连接读取失败"];
  }
  if (model.credentialState === "empty") {
    return ["暂无可用模型连接"];
  }
  const option = model.credentialOptions.find((item) => item.provider === model.settings.provider)
    ?? model.credentialOptions[0];
  if (!option) {
    return ["请选择模型连接"];
  }
  const items = [
    ...(skillLabel ? [skillLabel] : []),
    ...(model.settings.hookIds.length > 0 ? [`自动动作 ${model.settings.hookIds.length}`] : []),
    stripDefaultModelSuffix(option),
  ];
  const resolvedModelName = resolveSummaryModelName(model.settings.modelName, option.defaultModel);
  if (shouldShowModelSummaryItem(resolvedModelName, option.defaultModel)) {
    items.push(resolvedModelName);
  }
  const reasoningSummary = describeAssistantReasoningSelection(
    buildIncubatorReasoningDraftFields(model.settings),
    resolveAssistantReasoningControl({
      apiDialect: option.apiDialect,
      modelName: resolvedModelName === "跟随连接默认模型" ? option.defaultModel : resolvedModelName,
    }),
  );
  if (reasoningSummary) {
    items.push(reasoningSummary);
  }
  if (shouldShowTokenSummaryItem(model.settings.maxOutputTokens, option)) {
    items.push(`上限 ${resolveResolvedMaxOutputTokens(model.settings.maxOutputTokens, option)}`);
  }
  if (shouldShowOutputModeSummaryItem(model.settings.streamOutput, option)) {
    items.push(resolveChatOutputModeLabel(model.settings.streamOutput));
  }
  return items;
}

export function normalizeMaxOutputTokensInput(value: string) {
  return sanitizeAssistantOutputTokenInput(value);
}

export function syncProviderSelection(model: IncubatorChatModel, provider: string) {
  const currentOption = model.credentialOptions.find((item) => item.provider === model.settings.provider) ?? null;
  const option = model.credentialOptions.find((item) => item.provider === provider);
  model.setSettings((current) => {
    const nextModelName = option?.defaultModel ?? "";
    return {
      ...current,
      ...normalizeReasoningSettings(
        current,
        option?.apiDialect ?? null,
        nextModelName,
      ),
      maxOutputTokens: shouldSyncMaxOutputTokens(current.maxOutputTokens, currentOption, option),
      modelName: nextModelName,
      provider,
      streamOutput: prefersBufferedOutput(option ?? null) ? false : current.streamOutput,
    };
  });
}

function stripDefaultModelSuffix(option: IncubatorChatModel["credentialOptions"][number]) {
  if (!option.defaultModel) {
    return option.displayLabel;
  }
  const suffix = ` · ${option.defaultModel}`;
  return option.displayLabel.endsWith(suffix)
    ? option.displayLabel.slice(0, -suffix.length)
    : option.displayLabel;
}

function shouldSyncMaxOutputTokens(
  currentValue: string,
  currentOption: IncubatorChatModel["credentialOptions"][number] | null,
  nextOption: IncubatorChatModel["credentialOptions"][number] | undefined,
) {
  const normalizedCurrentValue = currentValue.trim();
  if (!normalizedCurrentValue) {
    return resolveOptionMaxOutputTokensDraft(nextOption ?? null);
  }
  if (normalizedCurrentValue !== resolveOptionMaxOutputTokensDraft(currentOption)) {
    return currentValue;
  }
  return resolveOptionMaxOutputTokensDraft(nextOption ?? null);
}

function resolveOptionMaxOutputTokensDraft(
  option: IncubatorChatModel["credentialOptions"][number] | null | undefined,
) {
  return String(option?.defaultMaxOutputTokens ?? resolveAssistantMaxOutputTokens(""));
}

function resolveSummaryModelName(modelName: string, defaultModel: string) {
  const normalizedModelName = modelName.trim();
  if (normalizedModelName) {
    return normalizedModelName;
  }
  const normalizedDefaultModel = defaultModel.trim();
  return normalizedDefaultModel || "跟随连接默认模型";
}

function shouldShowModelSummaryItem(modelName: string, defaultModel: string) {
  const normalizedDefaultModel = defaultModel.trim();
  if (!normalizedDefaultModel) {
    return modelName !== "跟随连接默认模型";
  }
  return modelName !== normalizedDefaultModel;
}

function shouldShowTokenSummaryItem(
  maxOutputTokens: string,
  option: IncubatorChatModel["credentialOptions"][number],
) {
  return resolveResolvedMaxOutputTokens(maxOutputTokens, option)
    !== resolveAssistantMaxOutputTokens(resolveOptionMaxOutputTokensDraft(option));
}

function shouldShowOutputModeSummaryItem(
  streamOutput: boolean,
  option: IncubatorChatModel["credentialOptions"][number],
) {
  return streamOutput !== !prefersBufferedOutput(option);
}

function resolveResolvedMaxOutputTokens(
  maxOutputTokens: string,
  option: IncubatorChatModel["credentialOptions"][number],
) {
  const normalizedValue = maxOutputTokens.trim() || resolveOptionMaxOutputTokensDraft(option);
  return resolveAssistantMaxOutputTokens(normalizedValue);
}

function normalizeReasoningSettings(
  settings: Pick<IncubatorChatModel["settings"], "reasoningEffort" | "thinkingBudget" | "thinkingLevel">,
  apiDialect: string | null,
  modelName: string,
) {
  const normalized = normalizeAssistantReasoningDraft(
    buildIncubatorReasoningDraftFields(settings),
    resolveAssistantReasoningControl({
      apiDialect,
      modelName,
    }),
  );
  return {
    reasoningEffort: normalized.reasoningEffort,
    thinkingBudget: normalized.thinkingBudget,
    thinkingLevel: normalized.thinkingLevel,
  };
}
