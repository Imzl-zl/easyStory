"use client";

import type { Dispatch, SetStateAction } from "react";
import type { useQueryClient } from "@tanstack/react-query";
import type { useRouter } from "next/navigation";

import {
  buildDuplicatedTemplateFormState,
  buildTemplateFormState,
  buildTemplateLibraryPath,
  createEmptyTemplateFormState,
  normalizeGuidedQuestionVariable,
  type TemplateEditorMode,
  type TemplateFeedback,
  type TemplateFormState,
  type TemplateVisibilityFilter,
} from "@/features/lobby/components/template-library-support";
import { listTemplates } from "@/lib/api/templates";
import type { TemplateDetail } from "@/lib/api/types";

type TemplateFeedbackSetter = Dispatch<SetStateAction<TemplateFeedback | null>>;
type TemplateEditorModeSetter = Dispatch<SetStateAction<TemplateEditorMode>>;
type TemplateFormSetter = Dispatch<SetStateAction<TemplateFormState>>;
type TemplateVisibilitySetter = Dispatch<SetStateAction<TemplateVisibilityFilter>>;
type TemplateTextSetter = Dispatch<SetStateAction<string>>;

export async function refreshTemplateQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  templateId: string,
  detail: TemplateDetail,
) {
  queryClient.setQueryData(["template", templateId], detail);
  await queryClient.invalidateQueries({ queryKey: ["templates"] });
}

export function resolveActiveTemplateId({
  initialTemplateId,
  filteredTemplates,
  searchText,
  visibility,
  genreFilter,
  templates,
  templatesLoaded,
}: {
  initialTemplateId: string | null;
  filteredTemplates: Array<{ id: string }>;
  searchText: string;
  visibility: TemplateVisibilityFilter;
  genreFilter: string;
  templates: Array<{ id: string }>;
  templatesLoaded: boolean;
}) {
  if (!templatesLoaded) {
    return initialTemplateId;
  }
  const hasScopedFilters =
    searchText.trim().length > 0 || visibility !== "all" || genreFilter !== "all";
  if (hasScopedFilters) {
    if (initialTemplateId && filteredTemplates.some((template) => template.id === initialTemplateId)) {
      return initialTemplateId;
    }
    return filteredTemplates[0]?.id ?? null;
  }
  if (initialTemplateId && templates.some((template) => template.id === initialTemplateId)) {
    return initialTemplateId;
  }
  return templates[0]?.id ?? null;
}

export function shouldSyncTemplateRoute({
  activeTemplateId,
  initialTemplateId,
  pathname,
}: {
  activeTemplateId: string | null;
  initialTemplateId: string | null;
  pathname: string;
}): boolean {
  if (!initialTemplateId) {
    return false;
  }
  return pathname !== buildTemplateLibraryPath(activeTemplateId);
}

export function selectTemplate({
  router,
  templateId,
  setEditorMode,
  setFeedback,
  setForm,
}: {
  router: ReturnType<typeof useRouter>;
  templateId: string;
  setEditorMode: TemplateEditorModeSetter;
  setFeedback: TemplateFeedbackSetter;
  setForm: TemplateFormSetter;
}) {
  resetEditorState({ setEditorMode, setFeedback, setForm });
  router.push(buildTemplateLibraryPath(templateId));
}

export function startEdit({
  detail,
  setEditorMode,
  setFeedback,
  setForm,
}: {
  detail: TemplateDetail | null;
  setEditorMode: TemplateEditorModeSetter;
  setFeedback: TemplateFeedbackSetter;
  setForm: TemplateFormSetter;
}) {
  if (!detail || detail.is_builtin) {
    setFeedback({ tone: "danger", message: "内建模板只读，请使用“基于此创建副本”。" });
    return;
  }
  setFeedback(null);
  setEditorMode("edit");
  setForm(buildTemplateFormState(detail));
}

export function startDuplicate({
  detail,
  templates,
  setEditorMode,
  setFeedback,
  setForm,
}: {
  detail: TemplateDetail | null;
  templates: Awaited<ReturnType<typeof listTemplates>>;
  setEditorMode: TemplateEditorModeSetter;
  setFeedback: TemplateFeedbackSetter;
  setForm: TemplateFormSetter;
}) {
  if (!detail) {
    setFeedback({ tone: "danger", message: "当前没有可复制的模板。" });
    return;
  }
  setFeedback({ tone: "info", message: "已把当前模板载入副本表单，保存后会创建新的自定义模板。" });
  setEditorMode("duplicate");
  setForm(buildDuplicatedTemplateFormState(detail, templates));
}

export function handleDelete({
  detail,
  mutate,
  setFeedback,
}: {
  detail: TemplateDetail | null;
  mutate: () => void;
  setFeedback: TemplateFeedbackSetter;
}) {
  if (!detail || detail.is_builtin) {
    setFeedback({ tone: "danger", message: "内建模板不允许删除。" });
    return;
  }
  if (!window.confirm(`确认删除模板「${detail.name}」？若仍被引用，后端会拒绝删除。`)) {
    return;
  }
  setFeedback(null);
  mutate();
}

export function submitEditor({
  activeTemplateId,
  detail,
  editorMode,
  createMutation,
  updateMutation,
  setFeedback,
}: {
  activeTemplateId: string | null;
  detail: TemplateDetail | null;
  editorMode: TemplateEditorMode;
  createMutation: () => void;
  updateMutation: () => void;
  setFeedback: TemplateFeedbackSetter;
}) {
  setFeedback(null);
  if (editorMode === "edit") {
    if (!activeTemplateId || !detail || detail.is_builtin) {
      setFeedback({ tone: "danger", message: "当前模板不可编辑，请重新选择自定义模板。" });
      return;
    }
    updateMutation();
    return;
  }
  createMutation();
}

export function resetEditorState({
  setEditorMode,
  setFeedback,
  setForm,
}: {
  setEditorMode: TemplateEditorModeSetter;
  setFeedback: TemplateFeedbackSetter;
  setForm: TemplateFormSetter;
}) {
  setEditorMode("create");
  setFeedback(null);
  setForm(createEmptyTemplateFormState());
}

export function addQuestionRow(setForm: TemplateFormSetter) {
  setForm((current) => ({
    ...current,
    guidedQuestions: [...current.guidedQuestions, { question: "", variable: "" }],
  }));
}

export function removeQuestionRow(setForm: TemplateFormSetter, index: number) {
  setForm((current) => ({
    ...current,
    guidedQuestions: current.guidedQuestions.filter((_, currentIndex) => currentIndex !== index),
  }));
}

export function updateQuestion(
  setForm: TemplateFormSetter,
  index: number,
  field: "question" | "variable",
  value: string,
) {
  setForm((current) => ({
    ...current,
    guidedQuestions: current.guidedQuestions.map((question, currentIndex) =>
      currentIndex === index ? { ...question, [field]: value } : question,
    ),
  }));
}

export function normalizeQuestionVariable(setForm: TemplateFormSetter, index: number) {
  setForm((current) => ({
    ...current,
    guidedQuestions: current.guidedQuestions.map((question, currentIndex) =>
      currentIndex === index
        ? { ...question, variable: normalizeGuidedQuestionVariable(question.variable) }
        : question,
    ),
  }));
}

export function setField<K extends keyof TemplateFormState>(
  setForm: TemplateFormSetter,
  field: K,
  value: TemplateFormState[K],
) {
  setForm((current) => ({ ...current, [field]: value }));
}

export function setSearchText(setter: TemplateTextSetter, value: string) {
  setter(value);
}

export function setGenreFilter(setter: TemplateTextSetter, value: string) {
  setter(value);
}

export function setVisibility(setter: TemplateVisibilitySetter, value: TemplateVisibilityFilter) {
  setter(value);
}
