"use client";

import type { TemplateLibraryModel } from "@/features/lobby/components/template-library-model";
import {
  formatGuidedQuestionVariableLabel,
  getTemplateEditorTitle,
  getTemplateSubmitLabel,
  normalizeGuidedQuestionVariable,
} from "@/features/lobby/components/template-library-support";

export function TemplateLibraryEditorPanel({ model }: { model: TemplateLibraryModel }) {
  return (
    <form className="panel-shell flex min-h-0 flex-col overflow-hidden p-5" onSubmit={(event) => { event.preventDefault(); model.submit(); }}>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        <EditorHeader mode={model.editorMode} />
        {model.feedback ? <FeedbackBanner feedback={model.feedback} /> : null}
        {model.formIssues.length > 0 ? <IssueList issues={model.formIssues} /> : null}
        <EditorFields model={model} />
        <GuidedQuestionEditor model={model} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="ink-button" disabled={model.isSubmitting || model.formIssues.length > 0} type="submit">
          {getTemplateSubmitLabel(model.editorMode, model.isSubmitting)}
        </button>
        <button className="ink-button-secondary" onClick={model.resetEditor} type="button">
          清空表单
        </button>
      </div>
    </form>
  );
}

function EditorHeader({ mode }: { mode: TemplateLibraryModel["editorMode"] }) {
  return (
    <div className="space-y-1">
      <h2 className="font-serif text-2xl font-semibold">{getTemplateEditorTitle(mode)}</h2>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">
        保存后会同步流程节点配置。
      </p>
    </div>
  );
}

function EditorFields({ model }: { model: TemplateLibraryModel }) {
  return (
    <>
      <FieldInput label="模板名称" value={model.form.name} onChange={(value) => model.setField("name", value)} />
      <FieldInput label="题材（可选）" value={model.form.genre} onChange={(value) => model.setField("genre", value)} />
      <FieldInput label="使用流程" value={model.form.workflowId} onChange={(value) => model.setField("workflowId", value)} />
      <label className="block">
        <span className="label-text">模板说明（可选）</span>
        <textarea className="ink-textarea" rows={4} value={model.form.description} onChange={(event) => model.setField("description", event.target.value)} />
      </label>
    </>
  );
}

function FieldInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="label-text">{label}</span>
      <input className="ink-input" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function GuidedQuestionEditor({ model }: { model: TemplateLibraryModel }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-serif text-lg font-semibold">引导问题</h3>
        <button className="ink-button-secondary" onClick={model.addQuestion} type="button">新增问题</button>
      </div>
      {model.form.guidedQuestions.length === 0 ? <p className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">未添加引导问题。</p> : null}
      {model.form.guidedQuestions.map((question, index) => (
        <QuestionCard key={`${index}-${question.variable}`} index={index} model={model} />
      ))}
    </section>
  );
}

function QuestionCard({
  index,
  model,
}: {
  index: number;
  model: TemplateLibraryModel;
}) {
  const question = model.form.guidedQuestions[index];
  return (
    <div className="panel-muted space-y-3 p-4">
      <label className="block">
        <span className="label-text">问题 #{index + 1}</span>
        <textarea className="ink-textarea" rows={3} value={question.question} onChange={(event) => model.updateQuestion(index, "question", event.target.value)} />
      </label>
      <label className="block">
        <span className="label-text">变量名</span>
        <input className="ink-input" value={question.variable} onBlur={() => model.normalizeQuestionVariable(index)} onChange={(event) => model.updateQuestion(index, "variable", event.target.value)} />
      </label>
      <div className="flex items-center justify-between gap-3 text-xs text-[var(--text-secondary)]">
        <span>
          保存时会自动规范变量名，例如
          {" "}
          <span className="font-medium">{formatGuidedQuestionVariableLabel("conflict")}</span>
          {" "}
          会转换为
          {" "}
          <code>{normalizeGuidedQuestionVariable("conflict")}</code>
          。
        </span>
        <button className="ink-button-danger" onClick={() => model.removeQuestion(index)} type="button">删除</button>
      </div>
    </div>
  );
}

function IssueList({ issues }: { issues: string[] }) {
  return (
    <div className="space-y-2 rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
      {issues.map((issue) => <p key={issue}>{issue}</p>)}
    </div>
  );
}

function FeedbackBanner({ feedback }: { feedback: NonNullable<TemplateLibraryModel["feedback"]> }) {
  const className = feedback.tone === "danger" ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]" : "bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]";
  return <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{feedback.message}</div>;
}
