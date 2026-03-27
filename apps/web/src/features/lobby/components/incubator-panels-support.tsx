"use client";

import { startTransition } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";

import { RequestStateInline } from "@/features/lobby/components/incubator-request-state";
import { getErrorMessage } from "@/lib/api/client";

import { type TemplateFormState } from "./incubator-page-support";
import type { IncubatorTemplateModel } from "./incubator-template-model";

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
        <h3 className="font-serif text-lg font-semibold">模板入口</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          适合已经有明确方向的用户。先选模板和项目名，再基于引导问题生成草稿。
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
      <SystemPoolField model={model} />
    </section>
  );
}

export function TemplateQuestionsCard({ model }: { model: IncubatorTemplateModel }) {
  const detailState = buildTemplateDetailState(model);
  return (
    <section className="panel-shell space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">引导问题</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          留空的问题不会提交；如果你改了答案，请重新生成草稿后再确认预览。
        </p>
      </div>
      <TemplateQuestionStatus model={model} state={detailState} />
      <TemplateQuestionList model={model} state={detailState} />
      <TemplateQuestionActions model={model} state={detailState} />
    </section>
  );
}

function TemplateMetaCard({ model }: { model: IncubatorTemplateModel }) {
  if (model.templateDetailQuery.isLoading) return <MetaNoticeCard tone="neutral">正在加载模板详情...</MetaNoticeCard>;
  if (model.templateDetailQuery.error) {
    return <MetaNoticeCard tone="danger">{getErrorMessage(model.templateDetailQuery.error)}</MetaNoticeCard>;
  }
  if (!model.templateDetailQuery.data) return null;
  return (
    <div className="rounded-3xl border border-[rgba(19,19,18,0.08)] bg-[rgba(255,255,255,0.54)] px-4 py-4">
      <p className="font-serif text-base font-semibold">{model.templateDetailQuery.data.name}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
        {model.templateDetailQuery.data.description ?? "当前模板未提供额外说明。"}
      </p>
      <dl className="mt-4 grid gap-2 text-sm text-[var(--text-secondary)]">
        <DetailRow label="默认工作流" value={model.templateDetailQuery.data.workflow_id ?? "未配置"} />
        <DetailRow label="引导问题" value={String(model.templateDetailQuery.data.guided_questions.length)} />
        <DetailRow label="节点数量" value={String(model.templateDetailQuery.data.nodes.length)} />
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
        <span className="block font-medium">允许系统凭证池</span>
        <span className="block text-sm leading-6 text-[var(--text-secondary)]">
          创建后的项目在运行期可参与系统默认凭证池策略。
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
      {state.isLoading ? <MetaNoticeCard tone="neutral">模板详情加载中，加载完成后才能生成草稿或直接创建项目。</MetaNoticeCard> : null}
      {state.errorMessage ? (
        <RequestStateInline
          action={
            <button className="ink-button-secondary" onClick={() => void model.templateDetailQuery.refetch()} type="button">
              重试模板详情
            </button>
          }
          message={state.errorMessage}
        />
      ) : null}
      {state.isReady && state.guidedQuestions.length === 0 ? (
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          当前模板没有配置引导问题，仍可直接创建空白设定项目。
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
        {model.draftMutation.isPending ? "生成中..." : "生成设定草稿"}
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
