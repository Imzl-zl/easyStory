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
  const items = [
    ...(skillLabel ? [skillLabel] : []),
    ...(model.settings.hookIds.length > 0 ? [`自动动作 ${model.settings.hookIds.length}`] : []),
    stripDefaultModelSuffix(option),
  ];
  const resolvedModelName = resolveSummaryModelName(model.settings.modelName, option.defaultModel);
  if (shouldShowModelSummaryItem(resolvedModelName, option.defaultModel)) {
    items.push(resolvedModelName);
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
