"use client";

import { startTransition, useCallback, useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { SectionCard } from "@/components/ui/section-card";
import { ChatModePanel } from "@/features/lobby/components/incubator-chat-panel";
import {
  TemplateModePanel,
} from "@/features/lobby/components/incubator-panels";
import {
  buildConversationDraftFingerprint,
  buildQuestionState,
  buildTemplateAnswers,
  buildTemplateDraftFingerprint,
  EMPTY_GUIDED_QUESTIONS,
  INCUBATOR_MODE_OPTIONS,
  INITIAL_CHAT_FORM,
  INITIAL_TEMPLATE_FORM,
  type ChatFormState,
  type IncubatorMode,
  type TemplateFormState,
} from "@/features/lobby/components/incubator-page-support";
import { getErrorMessage } from "@/lib/api/client";
import {
  buildIncubatorConversationDraft,
  buildIncubatorDraft,
  createProjectFromIncubator,
} from "@/lib/api/projects";
import { getTemplate, listTemplates } from "@/lib/api/templates";

type FeedbackState = {
  tone: "info" | "danger";
  message: string;
};

export function IncubatorPage() {
  const [mode, setMode] = useState<IncubatorMode>("template");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const templateModel = useIncubatorTemplateModel(setFeedback);
  const chatModel = useIncubatorChatModel(setFeedback);
  const handleModeChange = (nextMode: IncubatorMode) => {
    setMode(nextMode);
    setFeedback(null);
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title="Incubator"
        description="把模板问答、自由描述和模板建项目收口到独立路由，避免在 Lobby 内联堆状态。"
        action={<Link className="ink-button-secondary" href="/workspace/lobby">返回 Lobby</Link>}
      >
        <div className="space-y-5">
          <ModeTabs mode={mode} onModeChange={handleModeChange} />
          {feedback ? <FeedbackBanner feedback={feedback} /> : null}
          {mode === "template" ? (
            <TemplateModePanel model={templateModel} onSwitchToChat={() => handleModeChange("chat")} />
          ) : (
            <ChatModePanel model={chatModel} />
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function useIncubatorTemplateModel(
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>,
) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [form, setForm] = useState(INITIAL_TEMPLATE_FORM);
  const [draftFingerprint, setDraftFingerprint] = useState<string | null>(null);
  const templatesQuery = useQuery({ queryKey: ["templates"], queryFn: listTemplates });
  const templateDetailQuery = useQuery({
    queryKey: ["template", selectedTemplateId],
    queryFn: () => getTemplate(selectedTemplateId),
    enabled: Boolean(selectedTemplateId),
  });
  const templateDetail = templateDetailQuery.data ?? null;
  const guidedQuestions = templateDetail?.guided_questions ?? EMPTY_GUIDED_QUESTIONS;
  const answerValues = buildQuestionState(guidedQuestions, form.answerValues);
  const answers = buildTemplateAnswers(guidedQuestions, answerValues);
  const requestFingerprint = buildTemplateDraftFingerprint(selectedTemplateId, answers);

  const draftMutation = useMutation({
    mutationFn: () => {
      if (!templateDetail) {
        throw new Error("模板详情尚未加载完成，不能生成设定草稿。");
      }
      return buildIncubatorDraft({ template_id: selectedTemplateId, answers });
    },
    onSuccess: () => {
      setDraftFingerprint(requestFingerprint);
      setFeedback(buildInfoFeedback("模板设定草稿已生成。"));
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
  const createMutation = useMutation({
    mutationFn: () => {
      if (!templateDetail) {
        throw new Error("模板详情尚未加载完成，不能直接创建项目。");
      }
      return createProjectFromIncubator({
        name: form.projectName.trim(),
        template_id: selectedTemplateId,
        answers,
        allow_system_credential_pool: form.allowSystemCredentialPool,
      });
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/workspace/project/${result.project.id}/studio?panel=setting`);
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });
  const resetTemplateDraft = draftMutation.reset;
  const selectTemplate = useCallback((templateId: string) => {
    resetTemplateDraft();
    setDraftFingerprint(null);
    setSelectedTemplateId(templateId);
  }, [resetTemplateDraft]);
  useEffect(() => {
    syncSelectedTemplate(templatesQuery.data, selectedTemplateId, selectTemplate);
  }, [selectTemplate, selectedTemplateId, templatesQuery.data]);

  return {
    selectedTemplateId,
    selectTemplate,
    form: { ...form, answerValues },
    setForm,
    templatesQuery,
    templateDetailQuery,
    draftMutation,
    createMutation,
    isDraftStale:
      Boolean(draftMutation.data) && draftFingerprint !== null && draftFingerprint !== requestFingerprint,
  };
}

function useIncubatorChatModel(setFeedback: Dispatch<SetStateAction<FeedbackState | null>>) {
  const [form, setForm] = useState(INITIAL_CHAT_FORM);
  const [draftFingerprint, setDraftFingerprint] = useState<string | null>(null);
  const requestFingerprint = buildConversationDraftFingerprint(form);
  const draftMutation = useMutation({
    mutationFn: () =>
      buildIncubatorConversationDraft({
        conversation_text: form.conversationText.trim(),
        provider: form.provider.trim(),
        model_name: form.modelName.trim() || undefined,
      }),
    onSuccess: () => {
      setDraftFingerprint(requestFingerprint);
      setFeedback(buildInfoFeedback("自由描述草稿已生成。"));
    },
    onError: (error) => setFeedback(buildErrorFeedback(error)),
  });

  return {
    form,
    setForm,
    draftMutation,
    isDraftStale:
      Boolean(draftMutation.data) && draftFingerprint !== null && draftFingerprint !== requestFingerprint,
  };
}

function ModeTabs({
  mode,
  onModeChange,
}: {
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {INCUBATOR_MODE_OPTIONS.map((option) => (
          <button
            key={option.id}
            className="ink-tab"
            data-active={mode === option.id}
            onClick={() => onModeChange(option.id)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">
        {INCUBATOR_MODE_OPTIONS.find((option) => option.id === mode)?.description}
      </p>
    </div>
  );
}

function FeedbackBanner({ feedback }: { feedback: FeedbackState }) {
  const className =
    feedback.tone === "danger"
      ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
      : "bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]";

  return (
    <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{feedback.message}</div>
  );
}

function syncSelectedTemplate(
  templates: Awaited<ReturnType<typeof listTemplates>> | undefined,
  selectedTemplateId: string,
  selectTemplate: (templateId: string) => void,
) {
  if (!templates?.length) {
    return;
  }
  if (selectedTemplateId && templates.some((template) => template.id === selectedTemplateId)) {
    return;
  }
  startTransition(() => selectTemplate(templates[0].id));
}

function buildInfoFeedback(message: string): FeedbackState {
  return { tone: "info", message };
}

function buildErrorFeedback(error: unknown): FeedbackState {
  return { tone: "danger", message: getErrorMessage(error) };
}
