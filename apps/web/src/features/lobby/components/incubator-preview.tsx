"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildSettingIssueSummary,
  buildSettingSections,
  formatAppliedAnswerValue,
} from "@/features/lobby/components/incubator-page-support";
import type {
  ProjectIncubatorAppliedAnswer,
  ProjectIncubatorUnmappedAnswer,
  ProjectSetting,
  SettingCompletenessResult,
} from "@/lib/api/types";

type IncubatorPreviewProps = {
  title: string;
  description: string;
  emptyMessage: string;
  completeness?: SettingCompletenessResult;
  setting?: ProjectSetting;
  appliedAnswers?: ProjectIncubatorAppliedAnswer[];
  unmappedAnswers?: ProjectIncubatorUnmappedAnswer[];
  followUpQuestions?: string[];
  staleMessage?: string | null;
};

export function IncubatorPreview({
  title,
  description,
  emptyMessage,
  completeness,
  setting,
  appliedAnswers = [],
  unmappedAnswers = [],
  followUpQuestions = [],
  staleMessage = null,
}: IncubatorPreviewProps) {
  if (!setting || !completeness) {
    return <PlaceholderCard title={title} description={description} message={emptyMessage} />;
  }

  return (
    <div className="space-y-4">
      <CompletenessCard completeness={completeness} description={description} title={title} />
      {staleMessage ? <NoticeCard message={staleMessage} tone="warning" /> : null}
      <SettingPreviewCard setting={setting} />
      {appliedAnswers.length > 0 ? <AppliedAnswerCard answers={appliedAnswers} /> : null}
      {unmappedAnswers.length > 0 ? <UnmappedAnswerCard answers={unmappedAnswers} /> : null}
      {followUpQuestions.length > 0 ? (
        <QuestionListCard questions={followUpQuestions} title="建议继续补充的问题" />
      ) : null}
    </div>
  );
}

function CompletenessCard({
  title,
  description,
  completeness,
}: {
  title: string;
  description: string;
  completeness: SettingCompletenessResult;
}) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="font-serif text-lg font-semibold">{title}</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
        </div>
        <StatusBadge status={completeness.status} />
      </div>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">
        {buildSettingIssueSummary(completeness)}
      </p>
    </section>
  );
}

function SettingPreviewCard({ setting }: { setting: ProjectSetting }) {
  const sections = buildSettingSections(setting);

  return (
    <section className="panel-shell fan-panel space-y-4 p-5">
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">项目设定预览</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          这里展示后端返回的草稿结果，便于继续进入编辑器精修。
        </p>
      </header>
      {sections.length === 0 ? (
        <p className="text-sm leading-6 text-[var(--text-secondary)]">当前草稿还没有可展示字段。</p>
      ) : (
        sections.map((section) => (
          <div key={section.title} className="space-y-3">
            <h4 className="text-sm font-medium text-[var(--text-secondary)]">{section.title}</h4>
            <dl className="grid gap-3 md:grid-cols-2">
              {section.items.map((item) => (
                <div key={`${section.title}-${item.label}`} className="panel-muted space-y-1 p-4">
                  <dt className="text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">
                    {item.label}
                  </dt>
                  <dd className="text-sm leading-6 text-[var(--text-primary)]">{item.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))
      )}
    </section>
  );
}

function AppliedAnswerCard({ answers }: { answers: ProjectIncubatorAppliedAnswer[] }) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold">回答映射</h3>
      <div className="space-y-3">
        {answers.map((answer) => (
          <article key={`${answer.variable}-${answer.field_path}`} className="rounded-2xl bg-[rgba(255,255,255,0.52)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">
              {answer.variable}
              {" -> "}
              {answer.field_path}
            </p>
            <p className="mt-2 text-sm leading-6">{formatAppliedAnswerValue(answer.value)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function UnmappedAnswerCard({ answers }: { answers: ProjectIncubatorUnmappedAnswer[] }) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold">未映射回答</h3>
      <div className="space-y-3">
        {answers.map((answer) => (
          <article key={`${answer.variable}-${answer.reason}`} className="rounded-2xl bg-[rgba(255,255,255,0.52)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">
              {answer.variable}
            </p>
            <p className="mt-2 text-sm leading-6">{answer.value}</p>
            <p className="mt-1 text-xs text-[var(--accent-warning)]">{answer.reason}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function QuestionListCard({
  title,
  questions,
}: {
  title: string;
  questions: string[];
}) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold">{title}</h3>
      <ul className="space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
        {questions.map((question) => (
          <li key={question} className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3">
            {question}
          </li>
        ))}
      </ul>
    </section>
  );
}

function NoticeCard({
  message,
  tone,
}: {
  message: string;
  tone: "warning" | "info";
}) {
  const className =
    tone === "warning"
      ? "bg-[rgba(183,121,31,0.14)] text-[var(--accent-warning)]"
      : "bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]";

  return <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{message}</div>;
}

function PlaceholderCard({
  title,
  description,
  message,
}: {
  title: string;
  description: string;
  message: string;
}) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold">{title}</h3>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
      <p className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        {message}
      </p>
    </section>
  );
}
