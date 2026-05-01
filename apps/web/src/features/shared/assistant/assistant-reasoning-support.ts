"use client";

export type OpenAIReasoningEffort = "none" | "minimal" | "low" | "medium" | "high" | "xhigh";
export type GeminiThinkingLevel = "minimal" | "low" | "medium" | "high";

export type AssistantReasoningDraftFields = {
  reasoningEffort: string;
  thinkingBudget: string;
  thinkingLevel: string;
};

export type AssistantReasoningOption = {
  label: string;
  value: string;
};

export type AssistantReasoningPreferredKind = "openai" | "gemini_budget" | "gemini_level";

export type AssistantReasoningControl =
  | {
    description: string;
    kind: "none";
    title: string;
  }
  | {
    description: string;
    kind: "openai";
    options: AssistantReasoningOption[];
    title: string;
  }
  | {
    description: string;
    kind: "gemini_level";
    options: AssistantReasoningOption[];
    title: string;
  }
  | {
    allowDisable: boolean;
    allowDynamic: boolean;
    description: string;
    kind: "gemini_budget";
    maxBudget: number;
    minBudget: number;
    placeholder: string;
    title: string;
  };

const FOLLOW_DEFAULT_OPTION: AssistantReasoningOption = { label: "跟随模型默认", value: "" };
const ALL_OPENAI_REASONING_EFFORTS: OpenAIReasoningEffort[] = [
  "none",
  "minimal",
  "low",
  "medium",
  "high",
  "xhigh",
];
const ALL_GEMINI_THINKING_LEVELS: GeminiThinkingLevel[] = ["minimal", "low", "medium", "high"];

const OPENAI_REASONING_OPTION_LABELS: Record<OpenAIReasoningEffort, string> = {
  none: "关闭思考",
  minimal: "最少",
  low: "低",
  medium: "中",
  high: "高",
  xhigh: "极高",
};

const GEMINI_THINKING_OPTION_LABELS: Record<GeminiThinkingLevel, string> = {
  minimal: "最少",
  low: "低",
  medium: "中",
  high: "高",
};

export function resolveAssistantReasoningControl(options: {
  apiDialect?: string | null;
  modelName?: string | null;
  preferredKind?: AssistantReasoningPreferredKind | null;
}): AssistantReasoningControl {
  const apiDialect = normalizeOptionalText(options.apiDialect);
  const modelName = normalizeOptionalText(options.modelName).toLowerCase();
  const controlKind = resolveAssistantReasoningControlKind(
    apiDialect,
    modelName,
    options.preferredKind ?? null,
  );
  if (controlKind === "openai") {
    return {
      description: resolveOpenAIReasoningDescription(apiDialect, modelName),
      kind: "openai",
      options: [
        FOLLOW_DEFAULT_OPTION,
        ...buildOpenAIReasoningOptions(ALL_OPENAI_REASONING_EFFORTS),
      ],
      title: "思考强度",
    };
  }
  if (controlKind === "gemini_budget") {
    const budgetConfig = resolveGeminiBudgetConfig(modelName);
    return {
      allowDisable: budgetConfig.allowDisable,
      allowDynamic: budgetConfig.allowDynamic,
      description: budgetConfig.description,
      kind: "gemini_budget",
      maxBudget: budgetConfig.maxBudget,
      minBudget: budgetConfig.minBudget,
      placeholder: budgetConfig.placeholder,
      title: "思考预算",
    };
  }
  if (controlKind === "gemini_level") {
    return {
      description: resolveGeminiLevelDescription(modelName),
      kind: "gemini_level",
      options: [
        FOLLOW_DEFAULT_OPTION,
        ...resolveGeminiThinkingLevelOptions(modelName),
      ],
      title: "思考等级",
    };
  }
  return {
    description: "",
    kind: "none",
    title: "思考设置",
  };
}

export function sanitizeAssistantThinkingBudgetInput(value: string) {
  const compact = value.replace(/\s+/g, "");
  if (!compact) {
    return "";
  }
  const hasLeadingMinus = compact.startsWith("-");
  const digits = compact.replaceAll(/\D+/g, "");
  if (!digits) {
    return hasLeadingMinus ? "-" : "";
  }
  return hasLeadingMinus ? `-${digits}` : digits;
}

export function normalizeAssistantThinkingBudgetInput(value: string) {
  return sanitizeAssistantThinkingBudgetInput(value);
}

export function parseAssistantThinkingBudgetDraft(value: string) {
  const normalized = sanitizeAssistantThinkingBudgetInput(value);
  if (!normalized || normalized === "-") {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  return Number.isInteger(parsed) ? parsed : null;
}

export function resolveAssistantReasoningModelName(
  modelName: string | null | undefined,
  fallbackModelName: string | null | undefined,
) {
  return normalizeOptionalText(modelName) || normalizeOptionalText(fallbackModelName);
}

export function normalizeAssistantReasoningDraft(
  draft: AssistantReasoningDraftFields,
  control: AssistantReasoningControl,
): AssistantReasoningDraftFields {
  if (control.kind === "openai") {
    return {
      reasoningEffort: isAllowedOptionValue(control.options, draft.reasoningEffort) ? draft.reasoningEffort : "",
      thinkingBudget: "",
      thinkingLevel: "",
    };
  }
  if (control.kind === "gemini_level") {
    return {
      reasoningEffort: "",
      thinkingBudget: "",
      thinkingLevel: isAllowedOptionValue(control.options, draft.thinkingLevel) ? draft.thinkingLevel : "",
    };
  }
  if (control.kind === "gemini_budget") {
    const budget = parseAssistantThinkingBudgetDraft(draft.thinkingBudget);
    if (budget === null || budget < -1) {
      return { reasoningEffort: "", thinkingBudget: "", thinkingLevel: "" };
    }
    if (budget === -1 && control.allowDynamic) {
      return { reasoningEffort: "", thinkingBudget: "-1", thinkingLevel: "" };
    }
    if (budget === 0 && control.allowDisable) {
      return { reasoningEffort: "", thinkingBudget: "0", thinkingLevel: "" };
    }
    if (budget >= control.minBudget && budget <= control.maxBudget) {
      return { reasoningEffort: "", thinkingBudget: String(budget), thinkingLevel: "" };
    }
  }
  return {
    reasoningEffort: "",
    thinkingBudget: "",
    thinkingLevel: "",
  };
}

export function resolveAssistantReasoningPreferredKind(
  fields: AssistantReasoningDraftFields,
): AssistantReasoningPreferredKind | null {
  const normalizedReasoningEffort = normalizeOptionalText(fields.reasoningEffort);
  if (normalizedReasoningEffort) {
    return "openai";
  }
  const normalizedThinkingBudget = parseAssistantThinkingBudgetDraft(fields.thinkingBudget);
  if (normalizedThinkingBudget !== null) {
    return "gemini_budget";
  }
  const normalizedThinkingLevel = normalizeOptionalText(fields.thinkingLevel);
  if (normalizedThinkingLevel) {
    return "gemini_level";
  }
  return null;
}

export function buildAssistantReasoningShapeError(
  fields: AssistantReasoningDraftFields,
): string | null {
  const normalizedReasoningEffort = normalizeOptionalText(fields.reasoningEffort);
  const normalizedThinkingLevel = normalizeOptionalText(fields.thinkingLevel);
  const normalizedThinkingBudget = parseAssistantThinkingBudgetDraft(fields.thinkingBudget);
  if (normalizedThinkingLevel && normalizedThinkingBudget !== null) {
    return "thinking_level 与 thinking_budget 不能同时设置";
  }
  if (normalizedReasoningEffort && (normalizedThinkingLevel || normalizedThinkingBudget !== null)) {
    return "reasoning_effort 不能和 thinking_level 或 thinking_budget 同时存在";
  }
  return null;
}

export function buildAssistantReasoningPayload(
  draft: AssistantReasoningDraftFields,
  control: AssistantReasoningControl,
  options: {
    preserveInvalidShape?: boolean;
  } = {},
): {
  reasoning_effort?: OpenAIReasoningEffort;
  thinking_budget?: number;
  thinking_level?: GeminiThinkingLevel;
} {
  if (options.preserveInvalidShape && buildAssistantReasoningShapeError(draft)) {
    return buildAssistantReasoningRawPayload(draft);
  }
  const normalized = normalizeAssistantReasoningDraft(draft, control);
  if (control.kind === "openai" && normalized.reasoningEffort) {
    return { reasoning_effort: normalized.reasoningEffort as OpenAIReasoningEffort };
  }
  if (control.kind === "gemini_level" && normalized.thinkingLevel) {
    return { thinking_level: normalized.thinkingLevel as GeminiThinkingLevel };
  }
  if (control.kind === "gemini_budget") {
    const budget = parseAssistantThinkingBudgetDraft(normalized.thinkingBudget);
    if (budget !== null) {
      return { thinking_budget: budget };
    }
  }
  return {};
}

export function describeAssistantReasoningSelection(
  draft: AssistantReasoningDraftFields,
  control: AssistantReasoningControl,
): string | null {
  const normalized = normalizeAssistantReasoningDraft(draft, control);
  if (control.kind === "openai") {
    const option = control.options.find((item) => item.value === normalized.reasoningEffort);
    return option?.value ? `思考 ${option.label}` : null;
  }
  if (control.kind === "gemini_level") {
    const option = control.options.find((item) => item.value === normalized.thinkingLevel);
    return option?.value ? `思考 ${option.label}` : null;
  }
  if (control.kind === "gemini_budget") {
    const budget = parseAssistantThinkingBudgetDraft(normalized.thinkingBudget);
    if (budget === null) {
      return null;
    }
    if (budget === -1) {
      return "动态思考";
    }
    if (budget === 0) {
      return "关闭思考";
    }
    return `预算 ${budget}`;
  }
  return null;
}

function resolveOpenAIReasoningDescription(_apiDialect: string, _modelName: string) {
  return "控制模型思考深度";
}

function buildOpenAIReasoningOptions(
  values: ReadonlyArray<OpenAIReasoningEffort>,
): AssistantReasoningOption[] {
  return values.map((value) => ({
    label: OPENAI_REASONING_OPTION_LABELS[value],
    value,
  }));
}

function resolveGeminiThinkingLevelOptions(_modelName: string): AssistantReasoningOption[] {
  return ALL_GEMINI_THINKING_LEVELS.map((value) => ({
    label: GEMINI_THINKING_OPTION_LABELS[value],
    value,
  }));
}

function resolveGeminiLevelDescription(_modelName: string) {
  return "控制模型思考深度";
}

function resolveGeminiBudgetConfig(_modelName: string) {
  return {
    allowDisable: true,
    allowDynamic: true,
    description: "控制模型思考深度",
    maxBudget: Number.MAX_SAFE_INTEGER,
    minBudget: 1,
    placeholder: "留空跟随默认，或填 0 / -1 / 正整数",
  };
}

function buildAssistantReasoningRawPayload(
  draft: AssistantReasoningDraftFields,
): {
  reasoning_effort?: OpenAIReasoningEffort;
  thinking_budget?: number;
  thinking_level?: GeminiThinkingLevel;
} {
  const payload: {
    reasoning_effort?: OpenAIReasoningEffort;
    thinking_budget?: number;
    thinking_level?: GeminiThinkingLevel;
  } = {};
  const normalizedReasoningEffort = normalizeOptionalText(draft.reasoningEffort);
  const normalizedThinkingLevel = normalizeOptionalText(draft.thinkingLevel);
  const normalizedThinkingBudget = parseAssistantThinkingBudgetDraft(draft.thinkingBudget);
  if (normalizedReasoningEffort) {
    payload.reasoning_effort = normalizedReasoningEffort as OpenAIReasoningEffort;
  }
  if (normalizedThinkingLevel) {
    payload.thinking_level = normalizedThinkingLevel as GeminiThinkingLevel;
  }
  if (normalizedThinkingBudget !== null) {
    payload.thinking_budget = normalizedThinkingBudget;
  }
  return payload;
}

function resolveAssistantReasoningControlKind(
  apiDialect: string,
  modelName: string,
  preferredKind: AssistantReasoningPreferredKind | null,
): AssistantReasoningControl["kind"] {
  if (apiDialect === "openai_chat_completions" || apiDialect === "openai_responses") {
    return "openai";
  }
  if (apiDialect === "gemini_generate_content") {
    if (modelName.includes("gemini-2.5")) {
      return "gemini_budget";
    }
    if (!modelName) {
      return preferredKind ?? "gemini_level";
    }
    return "gemini_level";
  }
  if (apiDialect) {
    return "none";
  }
  if (modelName.startsWith("gpt-")) {
    return "openai";
  }
  if (modelName.includes("gemini-2.5")) {
    return "gemini_budget";
  }
  if (modelName.startsWith("gemini-")) {
    return "gemini_level";
  }
  return preferredKind ?? "none";
}

function normalizeOptionalText(value: string | null | undefined) {
  return typeof value === "string" ? value.trim() : "";
}

function isAllowedOptionValue(options: AssistantReasoningOption[], value: string) {
  return options.some((item) => item.value === value);
}
