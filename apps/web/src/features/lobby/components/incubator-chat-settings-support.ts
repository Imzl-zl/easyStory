"use client";

import {
  resolveAssistantMaxOutputTokens,
  sanitizeAssistantOutputTokenInput,
} from "@/features/shared/assistant/assistant-output-token-support";

import { prefersBufferedOutput } from "./incubator-chat-credential-support";
import { resolveChatOutputModeLabel } from "./incubator-chat-support";
import type { IncubatorChatModel } from "./incubator-page-model";

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
  const modelName = model.settings.modelName.trim() || option.defaultModel || "跟随连接默认模型";
  const maxOutputTokens = model.settings.maxOutputTokens.trim() || resolveOptionMaxOutputTokensDraft(option);
  return [
    ...(skillLabel ? [skillLabel] : []),
    ...(model.settings.hookIds.length > 0 ? [`自动动作 ${model.settings.hookIds.length}`] : []),
    stripDefaultModelSuffix(option),
    modelName,
    `上限 ${resolveAssistantMaxOutputTokens(maxOutputTokens)}`,
    resolveChatOutputModeLabel(model.settings.streamOutput),
  ];
}

export function normalizeMaxOutputTokensInput(value: string) {
  return sanitizeAssistantOutputTokenInput(value);
}

export function syncProviderSelection(model: IncubatorChatModel, provider: string) {
  const currentOption = model.credentialOptions.find((item) => item.provider === model.settings.provider) ?? null;
  const option = model.credentialOptions.find((item) => item.provider === provider);
  model.setSettings((current) => ({
    ...current,
    maxOutputTokens: shouldSyncMaxOutputTokens(current.maxOutputTokens, currentOption, option),
    modelName: option?.defaultModel ?? "",
    provider,
    streamOutput: prefersBufferedOutput(option ?? null) ? false : current.streamOutput,
  }));
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
