"use client";

import {
  sanitizeAssistantOutputTokenInput,
} from "@/features/shared/assistant/assistant-output-token-support";
import {
  ASSISTANT_DEFAULT_CHAT_SKILL_ID,
  ASSISTANT_DEFAULT_CHAT_SKILL_LABEL,
} from "@/features/shared/assistant/assistant-defaults";
import type { AssistantAgentDetail, AssistantAgentPayload } from "@/lib/api/types";

import {
  type AssistantMarkdownFrontmatter,
  assertFrontmatterKeys,
  parseAssistantMarkdownDocument,
  readOptionalFrontmatterBoolean,
  readOptionalFrontmatterInteger,
  readOptionalFrontmatterObject,
  readOptionalFrontmatterString,
  readRequiredFrontmatterString,
} from "./assistant-markdown-document-support";

export const ASSISTANT_AGENT_FILE_LABEL = "AGENT.md";

const DEFAULT_ASSISTANT_AGENT_PROMPT = [
  "你是 easyStory 里的长期创作搭子。",
  "先给结论，再陪用户把故事方向慢慢收拢。",
  "如果信息还不够，每次只追问一个关键问题。",
  "不要把回复写成表单，也不要一下子抛出太多选项。",
].join("\n");

export type AssistantAgentDraft = {
  defaultMaxOutputTokens: string;
  defaultModelName: string;
  defaultProvider: string;
  description: string;
  enabled: boolean;
  name: string;
  skillId: string;
  systemPrompt: string;
};

export function createEmptyAssistantAgentDraft(): AssistantAgentDraft {
  return {
    defaultMaxOutputTokens: "",
    defaultModelName: "",
    defaultProvider: "",
    description: "",
    enabled: true,
    name: "",
    skillId: ASSISTANT_DEFAULT_CHAT_SKILL_ID,
    systemPrompt: DEFAULT_ASSISTANT_AGENT_PROMPT,
  };
}

export function toAssistantAgentDraft(detail: AssistantAgentDetail): AssistantAgentDraft {
  return {
    defaultMaxOutputTokens: detail.default_max_output_tokens ? String(detail.default_max_output_tokens) : "",
    defaultModelName: detail.default_model_name ?? "",
    defaultProvider: detail.default_provider ?? "",
    description: detail.description ?? "",
    enabled: detail.enabled,
    name: detail.name,
    skillId: detail.skill_id,
    systemPrompt: detail.system_prompt,
  };
}

export function buildAssistantAgentPayload(draft: AssistantAgentDraft): AssistantAgentPayload {
  return {
    default_max_output_tokens: parseAssistantAgentMaxOutputTokens(draft.defaultMaxOutputTokens),
    default_model_name: normalizeOptionalText(draft.defaultModelName),
    default_provider: normalizeOptionalText(draft.defaultProvider),
    description: draft.description.trim(),
    enabled: draft.enabled,
    name: draft.name.trim(),
    skill_id: draft.skillId.trim(),
    system_prompt: draft.systemPrompt.trim(),
  };
}

export function buildAssistantAgentDocumentPreview(
  draft: AssistantAgentDraft,
  options: {
    agentId?: string | null;
  } = {},
) {
  const lines = ["---"];
  if (options.agentId) {
    lines.push(`id: ${options.agentId}`);
  }
  lines.push(`name: ${formatPreviewText(draft.name.trim() || "未命名 Agent")}`);
  lines.push(`enabled: ${draft.enabled ? "true" : "false"}`);
  lines.push(`skill_id: ${draft.skillId.trim() || ASSISTANT_DEFAULT_CHAT_SKILL_ID}`);
  if (draft.description.trim()) {
    lines.push(`description: ${formatPreviewText(draft.description.trim())}`);
  }
  const modelLines = buildAssistantAgentModelPreview(draft);
  if (modelLines.length > 0) {
    lines.push("model:");
    lines.push(...modelLines);
  }
  lines.push("---", "", draft.systemPrompt.trim() || DEFAULT_ASSISTANT_AGENT_PROMPT);
  return lines.join("\n");
}

export function parseAssistantAgentDocument(
  source: string,
  expectedId?: string | null,
): AssistantAgentDraft {
  const { body, frontmatter } = parseAssistantMarkdownDocument(source);
  assertFrontmatterKeys(
    frontmatter,
    ["description", "enabled", "id", "model", "name", "skill_id"],
    "AGENT.md frontmatter",
  );
  validateExpectedId(frontmatter, expectedId, "Agent");

  const model = readOptionalFrontmatterObject(frontmatter, "model", "AGENT.md model");
  if (model) {
    assertFrontmatterKeys(model, ["max_tokens", "name", "provider"], "AGENT.md model");
  }

  const systemPrompt = body.replace(/\s+$/, "");
  if (!systemPrompt.trim()) {
    throw new Error("AGENT.md 正文不能为空。");
  }

  return {
    defaultMaxOutputTokens: toTokenDraft(readOptionalFrontmatterInteger(model ?? {}, "max_tokens", "AGENT.md model.max_tokens")),
    defaultModelName: readOptionalFrontmatterString(model ?? {}, "name", "AGENT.md model.name") ?? "",
    defaultProvider: readOptionalFrontmatterString(model ?? {}, "provider", "AGENT.md model.provider") ?? "",
    description: readOptionalFrontmatterString(frontmatter, "description", "AGENT.md description") ?? "",
    enabled: readOptionalFrontmatterBoolean(frontmatter, "enabled", "AGENT.md enabled") ?? true,
    name: readRequiredFrontmatterString(frontmatter, "name", "AGENT.md name"),
    skillId: readRequiredFrontmatterString(frontmatter, "skill_id", "AGENT.md skill_id"),
    systemPrompt,
  };
}

export function isAssistantAgentDirty(
  draft: AssistantAgentDraft,
  detail: AssistantAgentDetail | null,
) {
  if (detail === null) {
    return hasDraftContent(draft);
  }
  return JSON.stringify(draft) !== JSON.stringify(toAssistantAgentDraft(detail));
}

export function sanitizeAssistantAgentMaxOutputTokensInput(value: string) {
  return sanitizeAssistantOutputTokenInput(value);
}

export function buildAssistantAgentListDescription(
  detail: Pick<AssistantAgentDetail, "description" | "enabled" | "skill_id">,
  skillLabel: string | null,
) {
  if (!detail.enabled) {
    return "已停用";
  }
  return detail.description?.trim() || `已绑定 ${skillLabel ?? ASSISTANT_DEFAULT_CHAT_SKILL_LABEL}`;
}

function normalizeOptionalText(value: string) {
  const normalized = value.trim();
  return normalized || null;
}

function parseAssistantAgentMaxOutputTokens(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  return Number.isInteger(parsed) ? parsed : null;
}

function hasDraftContent(draft: AssistantAgentDraft) {
  return Boolean(
    draft.name.trim()
      || draft.description.trim()
      || draft.systemPrompt.trim()
      || draft.defaultProvider.trim()
      || draft.defaultModelName.trim()
      || draft.defaultMaxOutputTokens.trim()
      || draft.skillId.trim() !== ASSISTANT_DEFAULT_CHAT_SKILL_ID,
  ) || !draft.enabled;
}

function buildAssistantAgentModelPreview(draft: AssistantAgentDraft) {
  const lines: string[] = [];
  const provider = normalizeOptionalText(draft.defaultProvider);
  const modelName = normalizeOptionalText(draft.defaultModelName);
  const maxTokens = parseAssistantAgentMaxOutputTokens(draft.defaultMaxOutputTokens);
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
  const parsedId = readOptionalFrontmatterString(frontmatter, "id", `AGENT.md ${label} id`);
  if (expectedId && parsedId && parsedId !== expectedId) {
    throw new Error(`${label} 的 id 由系统维护，不能在这里修改。`);
  }
}
