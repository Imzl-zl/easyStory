import type {
  TemplateDetail,
  TemplateGuidedQuestion,
  TemplateSummary,
  TemplateUpsertPayload,
} from "@/lib/api/types";

const LEGACY_GUIDED_QUESTION_VARIABLE_ALIASES: Record<string, string> = {
  conflict: "core_conflict",
};
const GUIDED_QUESTION_LABELS: Record<string, string> = {
  protagonist: "主角",
  world_setting: "世界设定",
  core_conflict: "核心冲突",
  genre: "题材",
  tone: "整体气质",
  target_readers: "目标读者",
  plot_direction: "剧情方向",
  special_requirements: "特殊要求",
};

export type TemplateEditorMode = "create" | "edit" | "duplicate";
export type TemplateVisibilityFilter = "all" | "builtin" | "custom";

export type TemplateFeedback = {
  tone: "info" | "danger";
  message: string;
};

export type TemplateFormState = {
  name: string;
  description: string;
  genre: string;
  workflowId: string;
  guidedQuestions: TemplateGuidedQuestion[];
};

export function createEmptyTemplateFormState(): TemplateFormState {
  return {
    name: "",
    description: "",
    genre: "",
    workflowId: "",
    guidedQuestions: [],
  };
}

export function buildTemplateFormState(template: TemplateDetail): TemplateFormState {
  return {
    name: template.name,
    description: template.description ?? "",
    genre: template.genre ?? "",
    workflowId: template.workflow_id ?? "",
    guidedQuestions: template.guided_questions.map((question) => ({ ...question })),
  };
}

export function buildDuplicatedTemplateFormState(
  template: TemplateDetail,
  templates: TemplateSummary[],
): TemplateFormState {
  return {
    ...buildTemplateFormState(template),
    name: buildDuplicatedTemplateName(template.name, templates),
  };
}

export function buildTemplatePayload(form: TemplateFormState): TemplateUpsertPayload {
  return {
    name: form.name.trim(),
    description: normalizeOptionalText(form.description),
    genre: normalizeOptionalText(form.genre),
    workflow_id: form.workflowId.trim(),
    guided_questions: form.guidedQuestions.map((question) => ({
      question: question.question.trim(),
      variable: normalizeGuidedQuestionVariable(question.variable),
    })),
  };
}

export function buildTemplateFormIssues({
  form,
  templates,
  editingTemplateId,
}: {
  form: TemplateFormState;
  templates: TemplateSummary[];
  editingTemplateId: string | null;
}): string[] {
  const issues: string[] = [];
  const normalizedName = normalizeRequiredText(form.name);
  const normalizedWorkflowId = normalizeRequiredText(form.workflowId);
  if (!normalizedName) {
    issues.push("模板名称不能为空。");
  }
  if (!normalizedWorkflowId) {
    issues.push("请填写要使用的流程。");
  }
  if (normalizedName && hasTemplateNameConflict(templates, normalizedName, editingTemplateId)) {
    issues.push(`模板名称已存在：${normalizedName}`);
  }
  const seenVariables = new Set<string>();
  form.guidedQuestions.forEach((question, index) => {
    const questionText = normalizeRequiredText(question.question);
    const variable = normalizeGuidedQuestionVariable(question.variable);
    if (!questionText || !variable) {
      issues.push(`问题 ${index + 1} 需要同时填写问题和变量名。`);
      return;
    }
    if (seenVariables.has(variable)) {
      issues.push(`变量名重复：${formatGuidedQuestionVariableLabel(variable)}`);
      return;
    }
    seenVariables.add(variable);
  });
  return issues;
}

export function filterTemplates({
  templates,
  keyword,
  visibility,
  genre,
}: {
  templates: TemplateSummary[];
  keyword: string;
  visibility: TemplateVisibilityFilter;
  genre: string;
}): TemplateSummary[] {
  const normalizedKeyword = keyword.trim().toLowerCase();
  return templates.filter((template) => {
    if (visibility === "builtin" && !template.is_builtin) {
      return false;
    }
    if (visibility === "custom" && template.is_builtin) {
      return false;
    }
    if (genre !== "all" && (template.genre ?? "") !== genre) {
      return false;
    }
    if (!normalizedKeyword) {
      return true;
    }
    const haystacks = [template.name, template.description ?? "", template.genre ?? ""];
    return haystacks.some((value) => value.toLowerCase().includes(normalizedKeyword));
  });
}

export function listTemplateGenres(templates: TemplateSummary[]): string[] {
  return Array.from(new Set(templates.flatMap((template) => (template.genre ? [template.genre] : []))))
    .sort((left, right) => left.localeCompare(right, "zh-CN"));
}

export function buildTemplateLibraryPath(templateId?: string | null): string {
  return templateId ? `/workspace/lobby/templates/${templateId}` : "/workspace/lobby/templates";
}

export function getTemplateEditorTitle(mode: TemplateEditorMode): string {
  if (mode === "edit") {
    return "编辑模板";
  }
  if (mode === "duplicate") {
    return "创建副本";
  }
  return "创建模板";
}

export function getTemplateSubmitLabel(mode: TemplateEditorMode, isPending: boolean): string {
  if (isPending) {
    return mode === "edit" ? "保存中…" : "创建中…";
  }
  return mode === "edit" ? "保存模板" : "创建模板";
}

export function normalizeGuidedQuestionVariable(value: string): string {
  const normalized = normalizeRequiredText(value);
  if (!normalized) {
    return "";
  }
  return LEGACY_GUIDED_QUESTION_VARIABLE_ALIASES[normalized] ?? normalized;
}

export function formatGuidedQuestionVariableLabel(value: string): string {
  const normalized = normalizeGuidedQuestionVariable(value);
  if (!normalized) {
    return "未分类";
  }
  return GUIDED_QUESTION_LABELS[normalized] ?? normalized.replaceAll("_", " ");
}

export function formatTemplateTime(value: string): string {
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildDuplicatedTemplateName(name: string, templates: TemplateSummary[]): string {
  const baseName = `${name.trim()} 副本`;
  if (!hasTemplateNameConflict(templates, baseName, null)) {
    return baseName;
  }
  let index = 2;
  while (hasTemplateNameConflict(templates, `${baseName} ${index}`, null)) {
    index += 1;
  }
  return `${baseName} ${index}`;
}

function hasTemplateNameConflict(
  templates: TemplateSummary[],
  name: string,
  editingTemplateId: string | null,
): boolean {
  return templates.some((template) => {
    if (editingTemplateId && template.id === editingTemplateId) {
      return false;
    }
    return template.name.trim().toLowerCase() === name.trim().toLowerCase();
  });
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function normalizeRequiredText(value: string): string {
  return value.trim();
}
