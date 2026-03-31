import type {
  ProjectIncubatorAnswer,
  ProjectIncubatorAppliedAnswer,
  ProjectSetting,
  SettingCompletenessResult,
  TemplateGuidedQuestion,
} from "@/lib/api/types";

export type TemplateFormState = {
  projectName: string;
  allowSystemCredentialPool: boolean;
  answerValues: Record<string, string>;
};

export const INITIAL_TEMPLATE_FORM: TemplateFormState = {
  projectName: "",
  allowSystemCredentialPool: false,
  answerValues: {},
};

export const EMPTY_GUIDED_QUESTIONS: TemplateGuidedQuestion[] = [];

export const INCUBATOR_MODE_OPTIONS = [
  {
    id: "chat",
    label: "AI 聊天",
    description: "通过对话整理项目草稿。",
  },
  {
    id: "template",
    label: "模板创建",
    description: "按模板填写信息并生成项目草稿。",
  },
] as const;

export type IncubatorMode = (typeof INCUBATOR_MODE_OPTIONS)[number]["id"];

export type SettingPreviewSection = {
  title: string;
  items: Array<{
    label: string;
    value: string;
  }>;
};

type SettingValue = string | number | string[] | null | undefined;

export function buildTemplateAnswers(
  questions: TemplateGuidedQuestion[],
  answerValues: Record<string, string>,
): ProjectIncubatorAnswer[] {
  return questions.flatMap((question) => {
    const value = answerValues[question.variable]?.trim();
    return value ? [{ variable: question.variable, value }] : [];
  });
}

export function buildTemplateDraftFingerprint(
  templateId: string,
  answers: ProjectIncubatorAnswer[],
): string {
  return JSON.stringify({ templateId, answers });
}

export function buildTemplatePreviewEmptyMessage({
  hasSelectedTemplate,
  isTemplateDetailLoading,
  templateDetailError,
}: {
  hasSelectedTemplate: boolean;
  isTemplateDetailLoading: boolean;
  templateDetailError: string | null;
}): string {
  if (templateDetailError) {
    return "模板内容暂未加载，无法生成草稿。";
  }
  if (!hasSelectedTemplate || isTemplateDetailLoading) {
    return "选择模板后可继续填写。";
  }
  return "填写问题后可生成项目草稿。";
}

export function buildQuestionState(
  questions: TemplateGuidedQuestion[],
  currentState: Record<string, string>,
): Record<string, string> {
  return Object.fromEntries(
    questions.map((question) => [question.variable, currentState[question.variable] ?? ""]),
  );
}

export function buildSettingIssueSummary(completeness?: SettingCompletenessResult): string {
  if (!completeness || completeness.issues.length === 0) {
    return "当前信息已基本完整。";
  }
  return completeness.issues
    .map((issue) => `${formatSettingFieldLabel(issue.field)}：${issue.message}`)
    .join(" / ");
}

export function buildSettingSections(setting: ProjectSetting): SettingPreviewSection[] {
  return [
    buildSection("基础设定", [
      ["题材", setting.genre],
      ["子题材", setting.sub_genre],
      ["目标读者", setting.target_readers],
      ["基调", setting.tone],
      ["核心冲突", setting.core_conflict],
      ["剧情方向", setting.plot_direction],
      ["特殊要求", setting.special_requirements],
    ]),
    buildSection("主角", [
      ["姓名", setting.protagonist?.name],
      ["身份", setting.protagonist?.identity],
      ["初始处境", setting.protagonist?.initial_situation],
      ["背景", setting.protagonist?.background],
      ["性格", setting.protagonist?.personality],
      ["目标", setting.protagonist?.goal],
    ]),
    buildSection("世界", [
      ["世界名称", setting.world_setting?.name],
      ["时代基线", setting.world_setting?.era_baseline],
      ["世界规则", setting.world_setting?.world_rules],
      ["力量体系", setting.world_setting?.power_system],
      ["关键地点", setting.world_setting?.key_locations],
    ]),
    buildSection("规模", [
      ["目标字数", setting.scale?.target_words],
      ["目标章节", setting.scale?.target_chapters],
      ["节奏", setting.scale?.pacing],
    ]),
  ].flatMap((section) => (section ? [section] : []));
}

export function formatAppliedAnswerValue(value: ProjectIncubatorAppliedAnswer["value"]): string {
  return Array.isArray(value) ? value.join(" / ") : String(value);
}

function buildSection(
  title: string,
  fields: Array<[string, SettingValue]>,
): SettingPreviewSection | null {
  const items = fields.flatMap(([label, rawValue]) => {
    const value = normalizeSettingValue(rawValue);
    return value ? [{ label, value }] : [];
  });
  if (items.length === 0) {
    return null;
  }
  return { title, items };
}

function normalizeSettingValue(value: SettingValue): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") {
    return value.trim() || null;
  }
  if (value.length === 0) {
    return null;
  }
  return value.join(" / ");
}

export function formatSettingFieldLabel(field: string): string {
  if (field === "genre") return "题材";
  if (field === "sub_genre") return "子题材";
  if (field === "target_readers") return "目标读者";
  if (field === "tone") return "整体气质";
  if (field === "core_conflict") return "核心冲突";
  if (field === "plot_direction") return "剧情方向";
  if (field === "special_requirements") return "特殊要求";
  if (field === "world_setting") return "世界设定";
  if (field === "scale") return "篇幅规划";
  if (field.startsWith("protagonist.")) return "主角设定";
  if (field.startsWith("world_setting.")) return "世界设定";
  if (field.startsWith("scale.")) return "篇幅规划";
  return field;
}
