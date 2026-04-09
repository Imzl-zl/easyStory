"use client";

import {
  sanitizeAssistantOutputTokenInput,
} from "@/features/shared/assistant/assistant-output-token-support";
import type { AssistantSkillDetail, AssistantSkillPayload } from "@/lib/api/types";

import {
  type AssistantMarkdownFrontmatter,
  assertFrontmatterKeys,
  parseAssistantMarkdownDocument,
  readOptionalFrontmatterBoolean,
  readOptionalFrontmatterInteger,
  readOptionalFrontmatterObject,
  readOptionalFrontmatterString,
  readRequiredFrontmatterString,
} from "@/features/settings/components/assistant/common/assistant-markdown-document-support";

export const ASSISTANT_SKILL_FILE_LABEL = "SKILL.md";
export const ASSISTANT_SKILL_VARIABLE_TIPS = [
  "{{ user_input }}",
  "{{ conversation_history }}",
] as const;

const DEFAULT_ASSISTANT_SKILL_CONTENT = [
  "你是一位擅长陪新手一起梳理故事方向的写作助手。",
  "先给 2 到 3 个可写方向，再告诉我你最推荐哪一个。",
  "如果信息还不够，每次只追问一个关键问题。",
  "",
  "用户输入：{{ user_input }}",
  "{% if conversation_history %}",
  "历史对话：{{ conversation_history }}",
  "{% endif %}",
].join("\n");

export type AssistantSkillDraft = {
  content: string;
  defaultMaxOutputTokens: string;
  defaultModelName: string;
  defaultProvider: string;
  description: string;
  enabled: boolean;
  name: string;
};

export function createEmptyAssistantSkillDraft(): AssistantSkillDraft {
  return {
    content: DEFAULT_ASSISTANT_SKILL_CONTENT,
    defaultMaxOutputTokens: "",
    defaultModelName: "",
    defaultProvider: "",
    description: "",
    enabled: true,
    name: "",
  };
}

export function toAssistantSkillDraft(detail: AssistantSkillDetail): AssistantSkillDraft {
  return {
    content: detail.content,
    defaultMaxOutputTokens: detail.default_max_output_tokens ? String(detail.default_max_output_tokens) : "",
    defaultModelName: detail.default_model_name ?? "",
    defaultProvider: detail.default_provider ?? "",
    description: detail.description ?? "",
    enabled: detail.enabled,
    name: detail.name,
  };
}

export function buildAssistantSkillPayload(draft: AssistantSkillDraft): AssistantSkillPayload {
  return {
    content: draft.content.trim(),
    default_max_output_tokens: parseAssistantSkillMaxOutputTokens(draft.defaultMaxOutputTokens),
    default_model_name: normalizeOptionalText(draft.defaultModelName),
    default_provider: normalizeOptionalText(draft.defaultProvider),
    description: draft.description.trim(),
    enabled: draft.enabled,
    name: draft.name.trim(),
  };
}

export function buildAssistantSkillDocumentPreview(
  draft: AssistantSkillDraft,
  options: {
    skillId?: string | null;
  } = {},
) {
  const lines = ["---"];
  if (options.skillId) {
    lines.push(`id: ${options.skillId}`);
  }
  lines.push(`name: ${formatPreviewText(draft.name.trim() || "未命名 Skill")}`);
  lines.push(`enabled: ${draft.enabled ? "true" : "false"}`);
  if (draft.description.trim()) {
    lines.push(`description: ${formatPreviewText(draft.description.trim())}`);
  }
  const modelLines = buildAssistantSkillModelPreview(draft);
  if (modelLines.length > 0) {
    lines.push("model:");
    lines.push(...modelLines);
  }
  lines.push("---", "", draft.content.trim() || DEFAULT_ASSISTANT_SKILL_CONTENT);
  return lines.join("\n");
}

export function parseAssistantSkillDocument(
  source: string,
  expectedId?: string | null,
): AssistantSkillDraft {
  const { body, frontmatter } = parseAssistantMarkdownDocument(source);
  assertFrontmatterKeys(frontmatter, ["description", "enabled", "id", "model", "name"], "SKILL.md frontmatter");
  validateExpectedId(frontmatter, expectedId, "Skill");

  const model = readOptionalFrontmatterObject(frontmatter, "model", "SKILL.md model");
  if (model) {
    assertFrontmatterKeys(model, ["max_tokens", "name", "provider"], "SKILL.md model");
  }

  const content = body.replace(/\s+$/, "");
  if (!content.trim()) {
    throw new Error("SKILL.md 正文不能为空。");
  }

  return {
    content,
    defaultMaxOutputTokens: toTokenDraft(readOptionalFrontmatterInteger(model ?? {}, "max_tokens", "SKILL.md model.max_tokens")),
    defaultModelName: readOptionalFrontmatterString(model ?? {}, "name", "SKILL.md model.name") ?? "",
    defaultProvider: readOptionalFrontmatterString(model ?? {}, "provider", "SKILL.md model.provider") ?? "",
    description: readOptionalFrontmatterString(frontmatter, "description", "SKILL.md description") ?? "",
    enabled: readOptionalFrontmatterBoolean(frontmatter, "enabled", "SKILL.md enabled") ?? true,
    name: readRequiredFrontmatterString(frontmatter, "name", "SKILL.md name"),
  };
}

export function isAssistantSkillDirty(
  draft: AssistantSkillDraft,
  detail: AssistantSkillDetail | null,
) {
  const baseline = detail ? toAssistantSkillDraft(detail) : createEmptyAssistantSkillDraft();
  return JSON.stringify(draft) !== JSON.stringify(baseline);
}

export function sanitizeAssistantSkillMaxOutputTokensInput(value: string) {
  return sanitizeAssistantOutputTokenInput(value);
}

export function buildAssistantSkillListDescription(detail: Pick<AssistantSkillDetail, "description" | "enabled">) {
  if (!detail.enabled) {
    return "已停用";
  }
  return detail.description?.trim() || "聊天里可直接切换";
}

function normalizeOptionalText(value: string) {
  const normalized = value.trim();
  return normalized || null;
}

function parseAssistantSkillMaxOutputTokens(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  return Number.isInteger(parsed) ? parsed : null;
}

function buildAssistantSkillModelPreview(draft: AssistantSkillDraft) {
  const lines: string[] = [];
  const provider = normalizeOptionalText(draft.defaultProvider);
  const modelName = normalizeOptionalText(draft.defaultModelName);
  const maxTokens = parseAssistantSkillMaxOutputTokens(draft.defaultMaxOutputTokens);
  if (provider) {
    lines.push(`  provider: ${formatPreviewText(provider)}`);
  }
  if (modelName) {
    lines.push(`  name: ${formatPreviewText(modelName)}`);
  }
  if (maxTokens !== null) {
    lines.push(`  max_tokens: ${maxTokens}`);
  }
  return lines;
}

function formatPreviewText(value: string) {
  return JSON.stringify(value);
}

function toTokenDraft(value: number | null) {
  return value === null ? "" : String(value);
}

function validateExpectedId(
  frontmatter: AssistantMarkdownFrontmatter,
  expectedId: string | null | undefined,
  label: string,
) {
  const parsedId = readOptionalFrontmatterString(frontmatter, "id", `SKILL.md ${label} id`);
  if (expectedId && parsedId && parsedId !== expectedId) {
    throw new Error(`${label} 的 id 由系统维护，不能在这里修改。`);
  }
}
