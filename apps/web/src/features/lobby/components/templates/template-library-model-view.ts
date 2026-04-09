"use client";

import type { Dispatch, SetStateAction } from "react";
import type { useQuery } from "@tanstack/react-query";
import type { useRouter } from "next/navigation";

import {
  addQuestionRow,
  handleDelete,
  normalizeQuestionVariable,
  removeQuestionRow,
  resetEditorState,
  selectTemplate,
  setField,
  startDuplicate,
  startEdit,
  submitEditor,
  updateQuestion,
} from "@/features/lobby/components/templates/template-library-model-support";
import type {
  TemplateEditorMode,
  TemplateFeedback,
  TemplateFormState,
  TemplateVisibilityFilter,
} from "@/features/lobby/components/templates/template-library-support";
import { listTemplateGenres } from "@/features/lobby/components/templates/template-library-support";
import { listTemplates } from "@/lib/api/templates";
import type { TemplateDetail } from "@/lib/api/types";

type TemplateStateShape = {
  editorMode: TemplateEditorMode;
  feedback: TemplateFeedback | null;
  form: TemplateFormState;
  genreFilter: string;
  searchText: string;
  visibility: TemplateVisibilityFilter;
  setEditorMode: Dispatch<SetStateAction<TemplateEditorMode>>;
  setFeedback: Dispatch<SetStateAction<TemplateFeedback | null>>;
  setForm: Dispatch<SetStateAction<TemplateFormState>>;
  setGenreFilter: Dispatch<SetStateAction<string>>;
  setSearchText: Dispatch<SetStateAction<string>>;
  setVisibility: Dispatch<SetStateAction<TemplateVisibilityFilter>>;
};

type TemplateMutationShape = {
  mutate: () => void;
  isPending: boolean;
};

export function buildTemplateLibraryModel({
  activeTemplateId,
  detailQuery,
  filteredTemplates,
  formIssues,
  templatesQuery,
  state,
  router,
  createMutation,
  updateMutation,
  deleteMutation,
}: {
  activeTemplateId: string | null;
  detailQuery: ReturnType<typeof useQuery<TemplateDetail>>;
  filteredTemplates: Awaited<ReturnType<typeof listTemplates>>;
  formIssues: string[];
  templatesQuery: ReturnType<typeof useQuery<Awaited<ReturnType<typeof listTemplates>>>>;
  state: TemplateStateShape;
  router: ReturnType<typeof useRouter>;
  createMutation: TemplateMutationShape;
  updateMutation: TemplateMutationShape;
  deleteMutation: TemplateMutationShape;
}) {
  return {
    ...buildTemplateLibraryStateSnapshot({
      activeTemplateId,
      createMutation,
      deleteMutation,
      detailQuery,
      filteredTemplates,
      formIssues,
      state,
      templatesQuery,
      updateMutation,
    }),
    ...buildTemplateLibraryActions({ deleteMutation, detailQuery, router, state }),
    ...buildTemplateLibraryEditorActions({
      activeTemplateId,
      createMutation,
      detailQuery,
      state,
      templatesQuery,
      updateMutation,
    }),
  };
}

function buildTemplateLibraryStateSnapshot({
  activeTemplateId,
  detailQuery,
  filteredTemplates,
  formIssues,
  templatesQuery,
  state,
  createMutation,
  updateMutation,
  deleteMutation,
}: {
  activeTemplateId: string | null;
  detailQuery: ReturnType<typeof useQuery<TemplateDetail>>;
  filteredTemplates: Awaited<ReturnType<typeof listTemplates>>;
  formIssues: string[];
  templatesQuery: ReturnType<typeof useQuery<Awaited<ReturnType<typeof listTemplates>>>>;
  state: TemplateStateShape;
  createMutation: TemplateMutationShape;
  updateMutation: TemplateMutationShape;
  deleteMutation: TemplateMutationShape;
}) {
  return {
    activeTemplateId,
    detailQuery,
    editorMode: state.editorMode,
    feedback: state.feedback,
    filteredTemplates,
    form: state.form,
    formIssues,
    genreFilter: state.genreFilter,
    genres: listTemplateGenres(templatesQuery.data ?? []),
    isDeletePending: deleteMutation.isPending,
    isSubmitting: createMutation.isPending || updateMutation.isPending,
    searchText: state.searchText,
    templatesQuery,
    visibility: state.visibility,
  };
}

function buildTemplateLibraryActions({
  detailQuery,
  deleteMutation,
  router,
  state,
}: {
  detailQuery: ReturnType<typeof useQuery<TemplateDetail>>;
  deleteMutation: TemplateMutationShape;
  router: ReturnType<typeof useRouter>;
  state: TemplateStateShape;
}) {
  return {
    deleteActive: () => handleDelete({ detail: detailQuery.data ?? null, mutate: deleteMutation.mutate, setFeedback: state.setFeedback }),
    normalizeQuestionVariable: (index: number) => normalizeQuestionVariable(state.setForm, index),
    removeQuestion: (index: number) => removeQuestionRow(state.setForm, index),
    resetEditor: () => resetEditorState(buildEditorSetters(state)),
    selectTemplate: (templateId: string) => selectTemplate({ router, templateId, ...buildEditorSetters(state) }),
    setField: <K extends keyof TemplateFormState>(field: K, value: TemplateFormState[K]) => setField(state.setForm, field, value),
    setGenreFilter: state.setGenreFilter,
    setSearchText: state.setSearchText,
    setVisibility: state.setVisibility,
  };
}

function buildTemplateLibraryEditorActions({
  activeTemplateId,
  detailQuery,
  templatesQuery,
  state,
  createMutation,
  updateMutation,
}: {
  activeTemplateId: string | null;
  detailQuery: ReturnType<typeof useQuery<TemplateDetail>>;
  templatesQuery: ReturnType<typeof useQuery<Awaited<ReturnType<typeof listTemplates>>>>;
  state: TemplateStateShape;
  createMutation: TemplateMutationShape;
  updateMutation: TemplateMutationShape;
}) {
  return {
    startCreate: () => resetEditorState(buildEditorSetters(state)),
    startDuplicate: () => startDuplicate({ detail: detailQuery.data ?? null, templates: templatesQuery.data ?? [], ...buildEditorSetters(state) }),
    startEdit: () => startEdit({ detail: detailQuery.data ?? null, ...buildEditorSetters(state) }),
    submit: () => submitEditor({ activeTemplateId, createMutation: createMutation.mutate, detail: detailQuery.data ?? null, editorMode: state.editorMode, setFeedback: state.setFeedback, updateMutation: updateMutation.mutate }),
    addQuestion: () => addQuestionRow(state.setForm),
    updateQuestion: (index: number, field: "question" | "variable", value: string) => updateQuestion(state.setForm, index, field, value),
  };
}

function buildEditorSetters(state: TemplateStateShape) {
  return {
    setEditorMode: state.setEditorMode,
    setFeedback: state.setFeedback,
    setForm: state.setForm,
  };
}
