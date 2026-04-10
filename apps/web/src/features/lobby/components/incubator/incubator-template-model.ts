"use client";

import { startTransition, useCallback, useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import {
  buildIncubatorDraft,
  createProjectFromIncubator,
} from "@/lib/api/projects";
import { getTemplate, listTemplates } from "@/lib/api/templates";
import type {
  ProjectIncubatorAnswer,
  ProjectIncubatorCreateResult,
  ProjectIncubatorDraft,
  TemplateDetail,
  TemplateSummary,
} from "@/lib/api/types";

import {
  buildErrorFeedback,
  buildInfoFeedback,
  type FeedbackState,
} from "@/features/lobby/components/incubator/incubator-feedback-support";
import {
  buildQuestionState,
  buildTemplateAnswers,
  buildTemplateDraftFingerprint,
  EMPTY_GUIDED_QUESTIONS,
  INITIAL_TEMPLATE_FORM,
  type TemplateFormState,
} from "@/features/lobby/components/incubator/incubator-page-support";

export type IncubatorTemplateModel = {
  selectedTemplateId: string;
  selectTemplate: (templateId: string) => void;
  form: TemplateFormState;
  setForm: Dispatch<SetStateAction<TemplateFormState>>;
  templatesQuery: UseQueryResult<TemplateSummary[]>;
  templateDetailQuery: UseQueryResult<TemplateDetail>;
  draftMutation: UseMutationResult<ProjectIncubatorDraft, unknown, void>;
  createMutation: UseMutationResult<ProjectIncubatorCreateResult, unknown, void>;
  isDraftStale: boolean;
};

type TemplateFormStateModel = {
  draftFingerprint: string | null;
  form: TemplateFormState;
  selectedTemplateId: string;
  setDraftFingerprint: Dispatch<SetStateAction<string | null>>;
  setForm: Dispatch<SetStateAction<TemplateFormState>>;
  setSelectedTemplateId: Dispatch<SetStateAction<string>>;
};

export function useIncubatorTemplateModel(
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
): IncubatorTemplateModel {
  const state = useTemplateState();
  const templatesQuery = useTemplateListQuery();
  const templateDetailQuery = useTemplateDetailQuery(state.selectedTemplateId);
  const requestData = buildTemplateRequestData(
    state.selectedTemplateId,
    templateDetailQuery.data,
    state.form.answerValues,
  );
  const draftMutation = useTemplateDraftMutation({
    requestData,
    setDraftFingerprint: state.setDraftFingerprint,
    setFeedback,
  });
  const createMutation = useTemplateCreateMutation({
    allowSystemCredentialPool: state.form.allowSystemCredentialPool,
    projectName: state.form.projectName,
    requestData,
    setFeedback,
  });
  const selectTemplate = useTemplateSelector(
    draftMutation.reset,
    state.setDraftFingerprint,
    state.setSelectedTemplateId,
  );

  useAutoSelectTemplate(
    templatesQuery.data,
    state.selectedTemplateId,
    selectTemplate,
  );

  return {
    selectedTemplateId: state.selectedTemplateId,
    selectTemplate,
    form: { ...state.form, answerValues: requestData.answerValues },
    setForm: state.setForm,
    templatesQuery,
    templateDetailQuery,
    draftMutation,
    createMutation,
    isDraftStale: isDraftStale(
      draftMutation.data,
      state.draftFingerprint,
      requestData.requestFingerprint,
    ),
  };
}

function useTemplateState(): TemplateFormStateModel {
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [form, setForm] = useState(INITIAL_TEMPLATE_FORM);
  const [draftFingerprint, setDraftFingerprint] = useState<string | null>(null);

  return {
    draftFingerprint,
    form,
    selectedTemplateId,
    setDraftFingerprint,
    setForm,
    setSelectedTemplateId,
  };
}

function useTemplateListQuery() {
  return useQuery({ queryKey: ["templates"], queryFn: listTemplates });
}

function useTemplateDetailQuery(selectedTemplateId: string) {
  return useQuery({
    queryKey: ["template", selectedTemplateId],
    queryFn: () => getTemplate(selectedTemplateId),
    enabled: Boolean(selectedTemplateId),
  });
}

function buildTemplateRequestData(
  selectedTemplateId: string,
  templateDetail: TemplateDetail | undefined,
  currentAnswerValues: Record<string, string>,
) {
  const guidedQuestions = templateDetail?.guided_questions ?? EMPTY_GUIDED_QUESTIONS;
  const answerValues = buildQuestionState(guidedQuestions, currentAnswerValues);
  const answers = buildTemplateAnswers(guidedQuestions, answerValues);

  return {
    answerValues,
    answers,
    requestFingerprint: buildTemplateDraftFingerprint(selectedTemplateId, answers),
    templateDetail: templateDetail ?? null,
  };
}

function useTemplateDraftMutation({
  requestData,
  setDraftFingerprint,
  setFeedback,
}: {
  requestData: ReturnType<typeof buildTemplateRequestData>;
  setDraftFingerprint: Dispatch<SetStateAction<string | null>>;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
}) {
  return useMutation({
    mutationFn: () =>
      createTemplateDraftRequest(
        requestData.templateDetail,
        requestData.answers,
      ),
    onSuccess: () => {
      setDraftFingerprint(requestData.requestFingerprint);
      setFeedback(buildInfoFeedback("模板设定草稿已生成。"));
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
}

function useTemplateCreateMutation({
  allowSystemCredentialPool,
  projectName,
  requestData,
  setFeedback,
}: {
  allowSystemCredentialPool: boolean;
  projectName: string;
  requestData: ReturnType<typeof buildTemplateRequestData>;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: () =>
      createTemplateProjectRequest(
        allowSystemCredentialPool,
        projectName,
        requestData.templateDetail,
        requestData.answers,
      ),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/workspace/project/${result.project.id}/studio?panel=setting&doc=${encodeURIComponent("项目说明.md")}`);
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
}

function useTemplateSelector(
  resetDraft: () => void,
  setDraftFingerprint: Dispatch<SetStateAction<string | null>>,
  setSelectedTemplateId: Dispatch<SetStateAction<string>>,
) {
  return useCallback(
    (templateId: string) => {
      resetDraft();
      setDraftFingerprint(null);
      setSelectedTemplateId(templateId);
    },
    [resetDraft, setDraftFingerprint, setSelectedTemplateId],
  );
}

function useAutoSelectTemplate(
  templates: TemplateSummary[] | undefined,
  selectedTemplateId: string,
  selectTemplate: (templateId: string) => void,
) {
  useEffect(() => {
    if (!templates?.length) {
      return;
    }
    if (selectedTemplateId && hasSelectedTemplate(templates, selectedTemplateId)) {
      return;
    }
    startTransition(() => selectTemplate(templates[0].id));
  }, [selectTemplate, selectedTemplateId, templates]);
}

function hasSelectedTemplate(
  templates: TemplateSummary[],
  selectedTemplateId: string,
) {
  return templates.some((template) => template.id === selectedTemplateId);
}

function createTemplateDraftRequest(
  templateDetail: TemplateDetail | null,
  answers: ProjectIncubatorAnswer[],
) {
  if (!templateDetail) {
    throw new Error("模板详情尚未加载完成，不能生成设定草稿。");
  }
  return buildIncubatorDraft({ template_id: templateDetail.id, answers });
}

function createTemplateProjectRequest(
  allowSystemCredentialPool: boolean,
  projectName: string,
  templateDetail: TemplateDetail | null,
  answers: ProjectIncubatorAnswer[],
) {
  if (!templateDetail) {
    throw new Error("模板详情尚未加载完成，不能直接创建项目。");
  }

  return createProjectFromIncubator({
    name: projectName.trim(),
    template_id: templateDetail.id,
    answers,
    allow_system_credential_pool: allowSystemCredentialPool,
  });
}

function isDraftStale(
  draft: ProjectIncubatorDraft | undefined,
  draftFingerprint: string | null,
  requestFingerprint: string,
) {
  return (
    Boolean(draft) &&
    draftFingerprint !== null &&
    draftFingerprint !== requestFingerprint
  );
}
