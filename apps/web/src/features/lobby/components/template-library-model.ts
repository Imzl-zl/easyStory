"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";

import { showAppNotice } from "@/components/ui/app-notice";
import {
  buildTemplateFormIssues,
  buildTemplateFormState,
  buildTemplateLibraryPath,
  buildTemplateMutationErrorFeedback,
  buildTemplateMutationErrorNotice,
  buildTemplateMutationSuccessNotice,
  buildTemplatePayload,
  createEmptyTemplateFormState,
  filterTemplates,
  type TemplateEditorMode,
  type TemplateFeedback,
  type TemplateFormState,
  type TemplateVisibilityFilter,
} from "@/features/lobby/components/template-library-support";
import {
  refreshTemplateQueries,
  resetEditorState,
  resolveActiveTemplateId,
  shouldSyncTemplateRoute,
} from "@/features/lobby/components/template-library-model-support";
import { buildTemplateLibraryModel } from "@/features/lobby/components/template-library-model-view";
import { getErrorMessage } from "@/lib/api/client";
import {
  createTemplate,
  deleteTemplate,
  getTemplate,
  listTemplates,
  updateTemplate,
} from "@/lib/api/templates";

export function useTemplateLibraryModel(initialTemplateId: string | null) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const state = useTemplateLibraryState();
  const templatesQuery = useQuery({ queryKey: ["templates"], queryFn: listTemplates });
  const filteredTemplates = useFilteredTemplates(state, templatesQuery.data ?? []);
  const activeTemplateId = resolveActiveTemplateId({
    initialTemplateId,
    filteredTemplates,
    searchText: state.deferredSearchText,
    visibility: state.visibility,
    genreFilter: state.genreFilter,
    templates: templatesQuery.data ?? [],
    templatesLoaded: templatesQuery.data !== undefined,
  });
  const detailQuery = useTemplateDetailQuery(activeTemplateId);
  const formIssues = useTemplateFormValidation(state, templatesQuery.data ?? [], activeTemplateId);
  const createMutation = useCreateTemplateMutation(queryClient, router, state);
  const updateMutation = useUpdateTemplateMutation(activeTemplateId, queryClient, state);
  const deleteMutation = useDeleteTemplateMutation(activeTemplateId, queryClient, router, state);

  useEffect(() => {
    if (
      templatesQuery.data === undefined ||
      !shouldSyncTemplateRoute({ activeTemplateId, initialTemplateId, pathname })
    ) {
      return;
    }
    router.replace(buildTemplateLibraryPath(activeTemplateId));
  }, [activeTemplateId, initialTemplateId, pathname, router, templatesQuery.data]);

  return buildTemplateLibraryModel({
    activeTemplateId,
    createMutation,
    deleteMutation,
    detailQuery,
    filteredTemplates,
    formIssues,
    router,
    state,
    templatesQuery,
    updateMutation,
  });
}

export type TemplateLibraryModel = ReturnType<typeof useTemplateLibraryModel>;

function useTemplateLibraryState() {
  const [searchText, setSearchText] = useState("");
  const [visibility, setVisibility] = useState<TemplateVisibilityFilter>("all");
  const [genreFilter, setGenreFilter] = useState("all");
  const [editorMode, setEditorMode] = useState<TemplateEditorMode>("create");
  const [feedback, setFeedback] = useState<TemplateFeedback | null>(null);
  const [form, setForm] = useState<TemplateFormState>(createEmptyTemplateFormState);
  const deferredSearchText = useDeferredValue(searchText);
  return {
    deferredSearchText,
    editorMode,
    feedback,
    form,
    genreFilter,
    searchText,
    setEditorMode,
    setFeedback,
    setForm,
    setGenreFilter,
    setSearchText,
    setVisibility,
    visibility,
  };
}

function useFilteredTemplates(
  state: ReturnType<typeof useTemplateLibraryState>,
  templates: Awaited<ReturnType<typeof listTemplates>>,
) {
  return useMemo(
    () =>
      filterTemplates({
        templates,
        keyword: state.deferredSearchText,
        visibility: state.visibility,
        genre: state.genreFilter,
      }),
    [state.deferredSearchText, state.genreFilter, state.visibility, templates],
  );
}

function useTemplateDetailQuery(activeTemplateId: string | null) {
  return useQuery({
    queryKey: ["template", activeTemplateId],
    queryFn: () => getTemplate(activeTemplateId as string),
    enabled: Boolean(activeTemplateId),
  });
}

function useTemplateFormValidation(
  state: ReturnType<typeof useTemplateLibraryState>,
  templates: Awaited<ReturnType<typeof listTemplates>>,
  activeTemplateId: string | null,
) {
  return useMemo(
    () =>
      buildTemplateFormIssues({
        form: state.form,
        templates,
        editingTemplateId: state.editorMode === "edit" ? activeTemplateId : null,
      }),
    [activeTemplateId, state.editorMode, state.form, templates],
  );
}

function useCreateTemplateMutation(
  queryClient: ReturnType<typeof useQueryClient>,
  router: ReturnType<typeof useRouter>,
  state: ReturnType<typeof useTemplateLibraryState>,
) {
  return useMutation({
    mutationFn: () => createTemplate(buildTemplatePayload(state.form)),
    onSuccess: async (result) => {
      await refreshTemplateQueries(queryClient, result.id, result);
      state.setFeedback(null);
      showAppNotice(buildTemplateMutationSuccessNotice("create"));
      state.setEditorMode("edit");
      state.setForm(buildTemplateFormState(result));
      router.push(buildTemplateLibraryPath(result.id));
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      state.setFeedback(buildTemplateMutationErrorFeedback(message));
      showAppNotice(buildTemplateMutationErrorNotice(message));
    },
  });
}

function useUpdateTemplateMutation(
  activeTemplateId: string | null,
  queryClient: ReturnType<typeof useQueryClient>,
  state: ReturnType<typeof useTemplateLibraryState>,
) {
  return useMutation({
    mutationFn: () => updateTemplate(activeTemplateId as string, buildTemplatePayload(state.form)),
    onSuccess: async (result) => {
      await refreshTemplateQueries(queryClient, result.id, result);
      state.setFeedback(null);
      showAppNotice(buildTemplateMutationSuccessNotice("update"));
      state.setEditorMode("edit");
      state.setForm(buildTemplateFormState(result));
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      state.setFeedback(buildTemplateMutationErrorFeedback(message));
      showAppNotice(buildTemplateMutationErrorNotice(message));
    },
  });
}

function useDeleteTemplateMutation(
  activeTemplateId: string | null,
  queryClient: ReturnType<typeof useQueryClient>,
  router: ReturnType<typeof useRouter>,
  state: ReturnType<typeof useTemplateLibraryState>,
) {
  return useMutation({
    mutationFn: () => deleteTemplate(activeTemplateId as string),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      state.setFeedback(null);
      showAppNotice(buildTemplateMutationSuccessNotice("delete"));
      resetEditorState({
        setEditorMode: state.setEditorMode,
        setFeedback: state.setFeedback,
        setForm: state.setForm,
      });
      router.push(buildTemplateLibraryPath());
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      state.setFeedback(buildTemplateMutationErrorFeedback(message));
      showAppNotice(buildTemplateMutationErrorNotice(message));
    },
  });
}
