import type {
  ProjectIncubatorAnswer,
  ProjectIncubatorAppliedAnswer,
  ProjectSetting,
  SettingCompletenessResult,
  TemplateGuidedQuestion,
} from "@/lib/api/types";

export const MAX_INCUBATOR_CONVERSATION_LENGTH = 8000;

export type TemplateFormState = {
  projectName: string;
  allowSystemCredentialPool: boolean;
  answerValues: Record<string, string>;
};

export type ChatFormState = {
  conversationText: string;
  provider: string;
  modelName: string;
};

export const INITIAL_TEMPLATE_FORM: TemplateFormState = {
  projectName: "",
  allowSystemCredentialPool: false,
  answerValues: {},
};

export const INITIAL_CHAT_FORM: ChatFormState = {
  conversationText: "",
  provider: "",
  modelName: "",
};

export const EMPTY_GUIDED_QUESTIONS: TemplateGuidedQuestion[] = [];

export const INCUBATOR_MODE_OPTIONS = [
  {
    id: "template",
    label: "模板问答",
    description: "选择模板、回答引导问题，先生成 Project Setting 草稿，再决定是否创建项目。",
  },
  {
    id: "chat",
    label: "自由描述",
    description: "输入一段创作意图，由后端提取设定草稿并返回后续补问。",
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

export function buildConversationDraftFingerprint(form: ChatFormState): string {
  return JSON.stringify({
    conversationText: form.conversationText.trim(),
    provider: form.provider.trim(),
    modelName: form.modelName.trim(),
  });
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
    return "模板详情加载失败，修复后才能生成预览。";
  }
  if (!hasSelectedTemplate || isTemplateDetailLoading) {
    return "正在准备模板详情，加载完成后再生成草稿。";
  }
  return "先填写模板回答，再点击“生成设定草稿”。";
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
    return "当前没有阻塞或警告项。";
  }
  return completeness.issues.map((issue) => `${issue.field}: ${issue.message}`).join(" / ");
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
