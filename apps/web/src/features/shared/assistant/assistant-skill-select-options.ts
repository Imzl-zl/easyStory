import {
  ASSISTANT_DEFAULT_CHAT_SKILL_ID,
  ASSISTANT_DEFAULT_CHAT_SKILL_LABEL,
} from "./assistant-defaults";

export type AssistantSkillSelectSource = {
  enabled?: boolean;
  id: string;
  name: string;
};

export type AssistantSkillSelectOption = {
  description?: string;
  label: string;
  value: string;
};

type BuildAssistantSkillSelectOptionsOptions = {
  defaultDescription?: string;
  disabledDescription?: string;
  includeDisabled?: boolean;
  includeSystemDefault?: boolean;
  leadingOptions?: AssistantSkillSelectOption[];
};

export function buildAssistantSkillSelectOptions(
  skills: ReadonlyArray<AssistantSkillSelectSource>,
  options: Readonly<BuildAssistantSkillSelectOptionsOptions> = {},
): AssistantSkillSelectOption[] {
  const includeDisabled = options.includeDisabled ?? false;
  const includeSystemDefault = options.includeSystemDefault ?? false;
  const visibleSkills = skills.filter((skill) => includeDisabled || skill.enabled !== false);
  const hasDefaultNameCollision = includeSystemDefault
    && visibleSkills.some((skill) => isDefaultChatSkillLabel(skill.name));
  const leadingOptions = options.leadingOptions ?? [];
  const systemDefaultOptions = includeSystemDefault
    ? [{
      description: options.defaultDescription,
      label: buildTaggedLabel(ASSISTANT_DEFAULT_CHAT_SKILL_LABEL, hasDefaultNameCollision ? ["系统"] : []),
      value: ASSISTANT_DEFAULT_CHAT_SKILL_ID,
    }]
    : [];

  return [
    ...leadingOptions,
    ...systemDefaultOptions,
    ...visibleSkills.map((skill) => ({
      description: buildCustomSkillDescription(skill, options.disabledDescription),
      label: buildCustomSkillLabel(skill, hasDefaultNameCollision),
      value: skill.id,
    })),
  ];
}

function buildCustomSkillDescription(
  skill: AssistantSkillSelectSource,
  disabledDescription: string | undefined,
) {
  if (skill.enabled === false) {
    return disabledDescription;
  }
  if (isDefaultChatSkillLabel(skill.name)) {
    return "你自己创建的 Skill";
  }
  return undefined;
}

function buildCustomSkillLabel(
  skill: AssistantSkillSelectSource,
  hasDefaultNameCollision: boolean,
) {
  const tags: string[] = [];
  if (hasDefaultNameCollision && isDefaultChatSkillLabel(skill.name)) {
    tags.push("自定义");
  }
  if (skill.enabled === false) {
    tags.push("已停用");
  }
  return buildTaggedLabel(skill.name, tags);
}

function buildTaggedLabel(label: string, tags: ReadonlyArray<string>) {
  const normalizedLabel = label.trim();
  if (tags.length === 0) {
    return normalizedLabel;
  }
  return `${normalizedLabel}（${tags.join("，")}）`;
}

function isDefaultChatSkillLabel(name: string) {
  return name.trim() === ASSISTANT_DEFAULT_CHAT_SKILL_LABEL;
}
