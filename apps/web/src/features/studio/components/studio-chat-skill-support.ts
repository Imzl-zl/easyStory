import type { AssistantSkillSummary } from "@/lib/api/types";

export type StudioChatSkillOption = {
  description: string | null;
  label: string;
  scope: "project" | "user";
  scopeLabel: "全局" | "项目";
  value: string;
};

export type StudioActiveSkillState = {
  conversationSkillId: string | null;
  conversationSkillLabel: string | null;
  detail: string | null;
  headline: string;
  nextTurnSkillId: string | null;
  nextTurnSkillLabel: string | null;
};

const STUDIO_LOADING_SKILL_LABEL = "正在读取 Skill…";

export function buildStudioChatSkillOptions(options: {
  projectSkills?: ReadonlyArray<AssistantSkillSummary>;
  userSkills?: ReadonlyArray<AssistantSkillSummary>;
}): StudioChatSkillOption[] {
  const seen = new Set<string>();
  return [
    ...withScope(options.projectSkills ?? [], "project"),
    ...withScope(options.userSkills ?? [], "user"),
  ].flatMap((skill) => {
    if (!skill.enabled || seen.has(skill.id)) {
      return [];
    }
    seen.add(skill.id);
    return [{
      description: normalizeDescription(skill.description),
      label: skill.name,
      scope: skill.scope,
      scopeLabel: skill.scope === "project" ? "项目" : "全局",
      value: skill.id,
    }];
  });
}

export function filterStudioChatSkillOptions(
  skillOptions: ReadonlyArray<StudioChatSkillOption>,
  query: string,
) {
  const normalizedQuery = normalizeSkillSearchQuery(query);
  if (!normalizedQuery) {
    return [...skillOptions];
  }
  return skillOptions.filter((option) => buildSkillSearchText(option).includes(normalizedQuery));
}

export function normalizeStudioSkillId(value: string | null | undefined) {
  const normalized = typeof value === "string" ? value.trim() : "";
  return normalized || null;
}

export function resolveStudioActiveSkillState(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
  skillsLoading?: boolean;
  skillOptions: ReadonlyArray<StudioChatSkillOption>;
}): StudioActiveSkillState {
  const conversationSkillId = normalizeStudioSkillId(options.conversationSkillId);
  const nextTurnSkillId = normalizeStudioSkillId(options.nextTurnSkillId);
  const normalizedNextTurnSkillId = nextTurnSkillId === conversationSkillId ? null : nextTurnSkillId;
  const conversationSkillLabel = resolveStudioSkillLabel(options.skillOptions, conversationSkillId, {
    skillsLoading: options.skillsLoading,
  });
  const nextTurnSkillLabel = resolveStudioSkillLabel(options.skillOptions, normalizedNextTurnSkillId, {
    skillsLoading: options.skillsLoading,
  });
  if (nextTurnSkillLabel && conversationSkillLabel) {
    return {
      conversationSkillId,
      conversationSkillLabel,
      detail: `成功发送后回到当前会话 · ${conversationSkillLabel}`,
      headline: `本次 · ${nextTurnSkillLabel}`,
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel,
    };
  }
  if (nextTurnSkillLabel) {
    return {
      conversationSkillId,
      conversationSkillLabel,
      detail: "只影响下一次成功发送，完成后自动清除",
      headline: `本次 · ${nextTurnSkillLabel}`,
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel,
    };
  }
  if (conversationSkillLabel) {
    return {
      conversationSkillId,
      conversationSkillLabel,
      detail: "后续消息都会沿用这个 Skill",
      headline: `当前会话 · ${conversationSkillLabel}`,
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    };
  }
  return {
    conversationSkillId: null,
    conversationSkillLabel: null,
    detail: "不额外套用 Skill，只使用规则、文稿上下文和当前会话。",
    headline: "普通对话",
    nextTurnSkillId: null,
    nextTurnSkillLabel: null,
  };
}

export function resolveStudioSkillLabel(
  skillOptions: ReadonlyArray<StudioChatSkillOption>,
  skillId: string | null,
  options: { skillsLoading?: boolean } = {},
) {
  if (!skillId) {
    return null;
  }
  const matchedOption = skillOptions.find((option) => option.value === skillId);
  if (matchedOption) {
    return matchedOption.label;
  }
  if (options.skillsLoading) {
    return STUDIO_LOADING_SKILL_LABEL;
  }
  return `已失效 Skill：${skillId}`;
}

function withScope(
  skills: ReadonlyArray<AssistantSkillSummary>,
  scope: StudioChatSkillOption["scope"],
) {
  return skills.map((skill) => ({ ...skill, scope }));
}

function normalizeDescription(value: string | null) {
  const normalized = value?.trim();
  return normalized || null;
}

function normalizeSkillSearchQuery(value: string) {
  return value.trim().toLocaleLowerCase();
}

function buildSkillSearchText(option: StudioChatSkillOption) {
  return [
    option.label,
    option.description,
    option.scopeLabel,
  ].filter(Boolean).join(" ").toLocaleLowerCase();
}
