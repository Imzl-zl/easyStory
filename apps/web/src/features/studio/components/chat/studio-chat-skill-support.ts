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

export type StudioUsableSkillSelection = {
  conversationSkillId: string | null;
  nextTurnSkillId: string | null;
};

export type StudioSkillLookupStatus = "loading" | "ready" | "error";
type StudioSkillSelectionIssue = "loading" | "error" | "invalid" | null;

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

export function normalizeStudioSkillSelection(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
}): StudioUsableSkillSelection {
  const conversationSkillId = normalizeStudioSkillId(options.conversationSkillId);
  const nextTurnSkillId = normalizeStudioSkillId(options.nextTurnSkillId);
  return {
    conversationSkillId,
    nextTurnSkillId: nextTurnSkillId === conversationSkillId ? null : nextTurnSkillId,
  };
}

export function hasStudioSelectedSkill(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
}) {
  const normalizedSelection = normalizeStudioSkillSelection(options);
  return Boolean(normalizedSelection.conversationSkillId || normalizedSelection.nextTurnSkillId);
}

export function resolveStudioSkillSendBlockReason(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
  skillLookupStatus: StudioSkillLookupStatus;
  skillOptions: ReadonlyArray<StudioChatSkillOption>;
}) {
  const issue = resolveStudioSkillSelectionIssue(options);
  if (issue === "loading") {
    return "当前 Skill 仍在确认中，确认完成后才能发送。";
  }
  if (issue === "error") {
    return "当前已选 Skill 暂时不可用，请稍后重试，或先切回普通对话。";
  }
  if (issue === "invalid") {
    return "当前已选 Skill 已失效，请重新选择或切回普通对话。";
  }
  return null;
}

export function resolveStudioUsableSkillSelection(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
  skillLookupReady?: boolean;
  skillOptions: ReadonlyArray<StudioChatSkillOption>;
}): StudioUsableSkillSelection {
  const normalizedSelection = normalizeStudioSkillSelection(options);
  if (!options.skillLookupReady) {
    return normalizedSelection;
  }
  const conversationSkillId = resolveStudioUsableSkillId(
    normalizedSelection.conversationSkillId,
    options.skillOptions,
  );
  const nextTurnSkillId = resolveStudioUsableSkillId(
    normalizedSelection.nextTurnSkillId,
    options.skillOptions,
  );
  return {
    conversationSkillId,
    nextTurnSkillId: nextTurnSkillId === conversationSkillId ? null : nextTurnSkillId,
  };
}

export function resolveStudioSendableSkillSelection(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
  skillLookupStatus: StudioSkillLookupStatus;
  skillOptions: ReadonlyArray<StudioChatSkillOption>;
}): StudioUsableSkillSelection {
  if (resolveStudioSkillSendBlockReason(options)) {
    return {
      conversationSkillId: null,
      nextTurnSkillId: null,
    };
  }
  return resolveStudioUsableSkillSelection({
    conversationSkillId: options.conversationSkillId,
    nextTurnSkillId: options.nextTurnSkillId,
    skillLookupReady: options.skillLookupStatus === "ready",
    skillOptions: options.skillOptions,
  });
}

export function resolveStudioActiveSkillState(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
  skillLookupStatus?: StudioSkillLookupStatus;
  skillsLoading?: boolean;
  skillOptions: ReadonlyArray<StudioChatSkillOption>;
}): StudioActiveSkillState {
  const normalizedSelection = normalizeStudioSkillSelection(options);
  const conversationSkillId = normalizedSelection.conversationSkillId;
  const normalizedNextTurnSkillId = normalizedSelection.nextTurnSkillId;
  const selectionIssue = resolveStudioSkillSelectionIssue({
    conversationSkillId,
    nextTurnSkillId: normalizedNextTurnSkillId,
    skillLookupStatus: options.skillLookupStatus ?? (options.skillsLoading ? "loading" : "ready"),
    skillOptions: options.skillOptions,
  });
  if (selectionIssue === "loading") {
    return {
      conversationSkillId,
      conversationSkillLabel: null,
      detail: null,
      headline: "Skill 待确认",
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel: null,
    };
  }
  if (selectionIssue === "error") {
    return {
      conversationSkillId,
      conversationSkillLabel: null,
      detail: null,
      headline: "Skill 暂不可用",
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel: null,
    };
  }
  if (selectionIssue === "invalid") {
    return {
      conversationSkillId,
      conversationSkillLabel: null,
      detail: null,
      headline: "Skill 已失效",
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel: null,
    };
  }
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
      detail: null,
      headline: `本次 · ${nextTurnSkillLabel}`,
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel,
    };
  }
  if (nextTurnSkillLabel) {
    return {
      conversationSkillId,
      conversationSkillLabel,
      detail: null,
      headline: `本次 · ${nextTurnSkillLabel}`,
      nextTurnSkillId: normalizedNextTurnSkillId,
      nextTurnSkillLabel,
    };
  }
  if (conversationSkillLabel) {
    return {
      conversationSkillId,
      conversationSkillLabel,
      detail: null,
      headline: `当前会话 · ${conversationSkillLabel}`,
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    };
  }
  return {
    conversationSkillId: null,
    conversationSkillLabel: null,
    detail: null,
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

function resolveStudioUsableSkillId(
  skillId: string | null | undefined,
  skillOptions: ReadonlyArray<StudioChatSkillOption>,
) {
  if (!skillId) {
    return null;
  }
  return skillOptions.some((option) => option.value === skillId)
    ? skillId
    : null;
}

function resolveStudioSkillSelectionIssue(options: {
  conversationSkillId?: string | null;
  nextTurnSkillId?: string | null;
  skillLookupStatus: StudioSkillLookupStatus;
  skillOptions: ReadonlyArray<StudioChatSkillOption>;
}): StudioSkillSelectionIssue {
  const normalizedSelection = normalizeStudioSkillSelection(options);
  if (!hasStudioSelectedSkill(normalizedSelection)) {
    return null;
  }
  if (options.skillLookupStatus === "loading") {
    return "loading";
  }
  if (options.skillLookupStatus === "error") {
    return "error";
  }
  const usableSelection = resolveStudioUsableSkillSelection({
    conversationSkillId: normalizedSelection.conversationSkillId,
    nextTurnSkillId: normalizedSelection.nextTurnSkillId,
    skillLookupReady: true,
    skillOptions: options.skillOptions,
  });
  return usableSelection.conversationSkillId === normalizedSelection.conversationSkillId
    && usableSelection.nextTurnSkillId === normalizedSelection.nextTurnSkillId
    ? null
    : "invalid";
}
