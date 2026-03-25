"use client";

import { startTransition } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";

import { EmptyState } from "@/components/ui/empty-state";
import { IncubatorPreview } from "@/features/lobby/components/incubator-preview";
import { buildTemplatePreviewEmptyMessage, type TemplateFormState } from "@/features/lobby/components/incubator-page-support";
import { RequestStateCard, RequestStateInline } from "@/features/lobby/components/incubator-request-state";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectIncubatorCreateResult, ProjectIncubatorDraft, TemplateDetail, TemplateSummary } from "@/lib/api/types";

type TemplateModePanelProps = {
  model: {
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
  onSwitchToChat: () => void;
};

export function TemplateModePanel({ model, onSwitchToChat }: TemplateModePanelProps) {
  const templateDetailError = model.templateDetailQuery.error ? getErrorMessage(model.templateDetailQuery.error) : null;
  const previewEmptyMessage = buildTemplatePreviewEmptyMessage({
    hasSelectedTemplate: model.selectedTemplateId.length > 0,
    isTemplateDetailLoading: model.selectedTemplateId.length > 0 && model.templateDetailQuery.isLoading,
    templateDetailError,
  });
  if (model.templatesQuery.isLoading) {
    return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载模板列表...</div>;
  }
  if (model.templatesQuery.error) {
    return (
      <RequestStateCard
        actions={
          <>
            <button
              className="ink-button-secondary"
              onClick={() => void model.templatesQuery.refetch()}
              type="button"
            >
              重试模板列表
            </button>
            <button className="ink-button-secondary" onClick={onSwitchToChat} type="button">
              切换到自由描述
            </button>
          </>
        }
        message={getErrorMessage(model.templatesQuery.error)}
        title="模板列表加载失败"
      />
    );
  }
  if ((model.templatesQuery.data?.length ?? 0) === 0) {
    return (
      <EmptyState
        title="当前没有模板"
        description="暂无可用模板，可切换到自由描述模式创建项目。"
        action={
          <button className="ink-button-secondary" onClick={onSwitchToChat} type="button">
            切换到自由描述
          </button>
        }
      />
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.84fr_1.16fr]">
      <div className="space-y-4">
        <TemplateControlCard model={model} />
        <TemplateQuestionsCard model={model} />
      </div>
      <IncubatorPreview
        title="模板草稿预览"
        description="回答问题后生成项目设定，并评估完整度。"
        emptyMessage={previewEmptyMessage}
        completeness={model.draftMutation.data?.setting_completeness}
        setting={model.draftMutation.data?.project_setting}
        appliedAnswers={model.draftMutation.data?.applied_answers}
        staleMessage={model.isDraftStale ? "你已修改模板回答，当前预览已过期，请重新生成草稿。" : null}
        unmappedAnswers={model.draftMutation.data?.unmapped_answers}
      />
    </div>
  );
}

function TemplateControlCard({ model }: Omit<TemplateModePanelProps, "onSwitchToChat">) {
  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">模板入口</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          先选模板和项目名。模板模式同时支持草稿预览与直接建项目。
        </p>
      </div>
      <label className="block">
        <span className="label-text">项目名称</span>
        <input
          className="ink-input"
          maxLength={255}
          value={model.form.projectName}
          onChange={(event) => setTemplateFormField(model.setForm, "projectName", event.target.value)}
        />
      </label>
      <label className="block">
        <span className="label-text">创作模板</span>
        <select
          className="ink-input"
          value={model.selectedTemplateId}
          onChange={(event) => startTransition(() => model.selectTemplate(event.target.value))}
        >
          {(model.templatesQuery.data ?? []).map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
              {template.genre ? ` · ${template.genre}` : ""}
            </option>
          ))}
        </select>
      </label>
      <TemplateMetaCard model={model} />
      <label className="panel-shell flex items-start gap-3 p-4">
        <input
          checked={model.form.allowSystemCredentialPool}
          className="mt-1 size-4 accent-[var(--accent-ink)]"
          onChange={(event) =>
            setTemplateFormField(model.setForm, "allowSystemCredentialPool", event.target.checked)
          }
          type="checkbox"
        />
        <span className="space-y-1">
          <span className="block font-medium">允许系统凭证池</span>
          <span className="block text-sm leading-6 text-[var(--text-secondary)]">
            创建后的项目在运行期可参与系统默认凭证池策略。
          </span>
        </span>
      </label>
    </section>
  );
}

function TemplateMetaCard({ model }: Omit<TemplateModePanelProps, "onSwitchToChat">) {
  if (model.templateDetailQuery.isLoading) {
    return (
      <div className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm text-[var(--text-secondary)]">
        正在加载模板详情...
      </div>
    );
  }
  if (model.templateDetailQuery.error) {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {getErrorMessage(model.templateDetailQuery.error)}
      </div>
    );
  }
  if (!model.templateDetailQuery.data) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-[rgba(19,19,18,0.08)] bg-[rgba(255,255,255,0.54)] px-4 py-4">
      <p className="font-serif text-base font-semibold">{model.templateDetailQuery.data.name}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
        {model.templateDetailQuery.data.description ?? "当前模板未提供额外说明。"}
      </p>
      <dl className="mt-4 grid gap-2 text-sm text-[var(--text-secondary)]">
        <div className="flex justify-between gap-4">
          <dt>默认工作流</dt>
          <dd>{model.templateDetailQuery.data.workflow_id ?? "未配置"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>引导问题</dt>
          <dd>{model.templateDetailQuery.data.guided_questions.length}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>节点数量</dt>
          <dd>{model.templateDetailQuery.data.nodes.length}</dd>
        </div>
      </dl>
    </div>
  );
}

function TemplateQuestionsCard({ model }: Omit<TemplateModePanelProps, "onSwitchToChat">) {
  const guidedQuestions = model.templateDetailQuery.data?.guided_questions ?? [];
  const isTemplateDetailLoading = model.selectedTemplateId.length > 0 && model.templateDetailQuery.isLoading;
  const templateDetailError = model.templateDetailQuery.error ? getErrorMessage(model.templateDetailQuery.error) : null;
  const isTemplateDetailReady = Boolean(model.templateDetailQuery.data);
  const canGenerateDraft = model.selectedTemplateId.length > 0 && isTemplateDetailReady && !model.draftMutation.isPending;
  const canCreate =
    model.selectedTemplateId.length > 0 &&
    isTemplateDetailReady &&
    model.form.projectName.trim().length > 0 &&
    !model.createMutation.isPending;

  return (
    <section className="panel-shell space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">引导问题</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          留空的问题不会提交；如果你改了答案，请重新生成草稿后再确认预览。
        </p>
      </div>
      {isTemplateDetailLoading ? (
        <p className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
          模板详情加载中，加载完成后才能生成草稿或直接创建项目。
        </p>
      ) : null}
      {templateDetailError ? (
        <RequestStateInline
          action={
            <button
              className="ink-button-secondary"
              onClick={() => void model.templateDetailQuery.refetch()}
              type="button"
            >
              重试模板详情
            </button>
          }
          message={templateDetailError}
        />
      ) : null}
      {isTemplateDetailReady && guidedQuestions.length === 0 ? (
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          当前模板没有配置引导问题，仍可直接创建空白设定项目。
        </p>
      ) : null}
      {isTemplateDetailReady
        ? guidedQuestions.map((question) => (
            <label key={question.variable} className="block">
              <span className="label-text">{question.question}</span>
              <textarea
                className="ink-textarea"
                rows={3}
                value={model.form.answerValues[question.variable] ?? ""}
                onChange={(event) =>
                  updateAnswerValue(model.setForm, question.variable, event.target.value)
                }
              />
            </label>
          ))
        : null}
      <div className="flex flex-wrap gap-2">
        <button
          className="ink-button-secondary"
          disabled={!canGenerateDraft}
          onClick={() => model.draftMutation.mutate()}
          type="button"
        >
          {model.draftMutation.isPending ? "生成中..." : "生成设定草稿"}
        </button>
        <button
          className="ink-button"
          disabled={!canCreate}
          onClick={() => model.createMutation.mutate()}
          type="button"
        >
          {model.createMutation.isPending ? "创建中..." : "直接创建项目"}
        </button>
      </div>
    </section>
  );
}

function setTemplateFormField<K extends keyof TemplateFormState>(
  setForm: Dispatch<SetStateAction<TemplateFormState>>,
  field: K,
  value: TemplateFormState[K],
) {
  setForm((current) => ({ ...current, [field]: value }));
}

function updateAnswerValue(
  setForm: Dispatch<SetStateAction<TemplateFormState>>,
  variable: string,
  value: string,
) {
  setForm((current) => ({
    ...current,
    answerValues: { ...current.answerValues, [variable]: value },
  }));
}
