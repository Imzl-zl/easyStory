import type {
  ProjectIncubatorAnswer,
  ProjectIncubatorAppliedAnswer,
  TemplateGuidedQuestion,
} from "@/lib/api/types";
export {
  buildProjectSettingIssueSummary as buildSettingIssueSummary,
  buildProjectSettingSections as buildSettingSections,
  formatProjectSettingFieldLabel as formatSettingFieldLabel,
  type SettingPreviewSection,
} from "@/features/project/components/project-setting-summary-support";

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

export function formatAppliedAnswerValue(value: ProjectIncubatorAppliedAnswer["value"]): string {
  return Array.isArray(value) ? value.join(" / ") : String(value);
}
