"use client";

import { startTransition } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";

import { AppSelect } from "@/components/ui/app-select";
import { RequestStateInline } from "@/features/lobby/components/common/request-state";
import { getErrorMessage } from "@/lib/api/client";

import { type TemplateFormState } from "@/features/lobby/components/incubator/incubator-page-support";
import type { IncubatorTemplateModel } from "@/features/lobby/components/incubator/incubator-template-model";

type TemplateDetailState = {
  canCreate: boolean;
  canGenerateDraft: boolean;
  guidedQuestions: NonNullable<IncubatorTemplateModel["templateDetailQuery"]["data"]>["guided_questions"];
  isReady: boolean;
  isLoading: boolean;
  errorMessage: string | null;
};

export function TemplateControlCard({ model }: { model: IncubatorTemplateModel }) {
  return (
    <section className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">选择模板</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          选择模板后可继续填写项目信息。
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
        <AppSelect
          disabled={(model.templatesQuery.data ?? []).length === 0}
          options={(model.templatesQuery.data ?? []).map((template) => ({
            description: template.genre || undefined,
            label: template.name,
            value: template.id,
          }))}
          placeholder="选择模板"
          value={model.selectedTemplateId}
          onChange={(value) => startTransition(() => model.selectTemplate(value))}
        />
      </label>
      <TemplateMetaCard model={model} />
      <SystemPoolField model={model} />
    </section>
  );
}

export function TemplateQuestionsCard({ model }: { model: IncubatorTemplateModel }) {
  const detailState = buildTemplateDetailState(model);
  return (
    <section className="panel-shell space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">补充信息</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          按需填写后可生成项目草稿。
        </p>
      </div>
      <TemplateQuestionStatus model={model} state={detailState} />
      <TemplateQuestionList model={model} state={detailState} />
      <TemplateQuestionActions model={model} state={detailState} />
    </section>
  );
}

function TemplateMetaCard({ model }: { model: IncubatorTemplateModel }) {
  if (model.templateDetailQuery.isLoading) return <MetaNoticeCard tone="neutral">正在读取模板信息…</MetaNoticeCard>;
  if (model.templateDetailQuery.error) {
    return <MetaNoticeCard tone="danger">{getErrorMessage(model.templateDetailQuery.error)}</MetaNoticeCard>;
  }
  if (!model.templateDetailQuery.data) return null;
  return (
    <div className="rounded-3xl border border-[rgba(19,19,18,0.08)] bg-[rgba(255,255,255,0.54)] px-4 py-4">
      <p className="font-serif text-base font-semibold">{model.templateDetailQuery.data.name}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
        {model.templateDetailQuery.data.description ?? "暂无说明。"}
      </p>
      <dl className="mt-4 grid gap-2 text-sm text-[var(--text-secondary)]">
        <DetailRow label="流程" value={model.templateDetailQuery.data.workflow_id ?? "未设置"} />
        <DetailRow label="问题数" value={String(model.templateDetailQuery.data.guided_questions.length)} />
        <DetailRow label="节点数" value={String(model.templateDetailQuery.data.nodes.length)} />
      </dl>
    </div>
  );
}

function SystemPoolField({ model }: { model: IncubatorTemplateModel }) {
  return (
    <label className="panel-shell flex items-start gap-3 p-4">
      <input
        checked={model.form.allowSystemCredentialPool}
        className="mt-1 size-4 accent-[var(--accent-ink)]"
        onChange={(event) => setTemplateFormField(model.setForm, "allowSystemCredentialPool", event.target.checked)}
        type="checkbox"
      />
      <span className="space-y-1">
        <span className="block font-medium">创建项目后沿用默认模型连接</span>
        <span className="block text-sm leading-6 text-[var(--text-secondary)]">
          仅影响创建后的项目。
        </span>
      </span>
    </label>
  );
}

function buildTemplateDetailState(model: IncubatorTemplateModel): TemplateDetailState {
  const isReady = Boolean(model.templateDetailQuery.data);
  return {
    canCreate: model.selectedTemplateId.length > 0 && isReady && model.form.projectName.trim().length > 0 && !model.createMutation.isPending,
    canGenerateDraft: model.selectedTemplateId.length > 0 && isReady && !model.draftMutation.isPending,
    guidedQuestions: model.templateDetailQuery.data?.guided_questions ?? [],
    isReady,
    isLoading: model.selectedTemplateId.length > 0 && model.templateDetailQuery.isLoading,
    errorMessage: model.templateDetailQuery.error ? getErrorMessage(model.templateDetailQuery.error) : null,
  };
}

function TemplateQuestionStatus({
  model,
  state,
}: {
  model: IncubatorTemplateModel;
  state: TemplateDetailState;
}) {
  return (
    <>
      {state.isLoading ? <MetaNoticeCard tone="neutral">模板加载中。</MetaNoticeCard> : null}
      {state.errorMessage ? (
        <RequestStateInline
          action={
            <button className="ink-button-secondary" onClick={() => void model.templateDetailQuery.refetch()} type="button">
              重试读取模板
            </button>
          }
          message={state.errorMessage}
        />
      ) : null}
      {state.isReady && state.guidedQuestions.length === 0 ? (
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          当前模板无需补充问题，可直接整理草稿或创建项目。
        </p>
      ) : null}
    </>
  );
}

function TemplateQuestionList({
  model,
  state,
}: {
  model: IncubatorTemplateModel;
  state: TemplateDetailState;
}) {
  if (!state.isReady) return null;
  return state.guidedQuestions.map((question) => (
    <label key={question.variable} className="block">
      <span className="label-text">{question.question}</span>
      <textarea
        className="ink-textarea"
        rows={3}
        value={model.form.answerValues[question.variable] ?? ""}
        onChange={(event) => updateAnswerValue(model.setForm, question.variable, event.target.value)}
      />
    </label>
  ));
}

function TemplateQuestionActions({
  model,
  state,
}: {
  model: IncubatorTemplateModel;
  state: TemplateDetailState;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button className="ink-button-secondary" disabled={!state.canGenerateDraft} onClick={() => model.draftMutation.mutate()} type="button">
        {model.draftMutation.isPending ? "整理中…" : "整理项目草稿"}
      </button>
      <button className="ink-button" disabled={!state.canCreate} onClick={() => model.createMutation.mutate()} type="button">
        {model.createMutation.isPending ? "创建中..." : "直接创建项目"}
      </button>
    </div>
  );
}

function MetaNoticeCard({ children, tone }: { children: ReactNode; tone: "danger" | "neutral" }) {
  const className = tone === "danger"
    ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
    : "bg-[rgba(255,255,255,0.52)] text-[var(--text-secondary)]";
  return <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{children}</div>;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return <div className="flex justify-between gap-4"><dt>{label}</dt><dd>{value}</dd></div>;
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
  setForm((current) => ({ ...current, answerValues: { ...current.answerValues, [variable]: value } }));
}
