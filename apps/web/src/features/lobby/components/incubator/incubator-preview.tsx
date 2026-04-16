"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildSettingIssueSummary,
  buildSettingSections,
  formatSettingFieldLabel,
  formatAppliedAnswerValue,
} from "@/features/lobby/components/incubator/incubator-page-support";
import type {
  ProjectIncubatorAppliedAnswer,
  ProjectIncubatorUnmappedAnswer,
  ProjectSetting,
  SettingCompletenessResult,
} from "@/lib/api/types";

type IncubatorPreviewProps = {
  title: string;
  description?: string;
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
        <QuestionListCard questions={followUpQuestions} title="待补充" />
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
  description?: string;
  completeness: SettingCompletenessResult;
}) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="font-serif text-lg font-semibold">{title}</h3>
          <p className="text-sm leading-6 text-text-secondary">{description}</p>
        </div>
        <StatusBadge status={completeness.status} />
      </div>
      <p className="text-sm leading-6 text-text-secondary">
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
        <h3 className="font-serif text-lg font-semibold">草稿内容</h3>
        <p className="text-sm leading-6 text-text-secondary">
          可继续修改。
        </p>
      </header>
      {sections.length === 0 ? (
        <p className="text-sm leading-6 text-text-secondary">暂无可展示内容。</p>
      ) : (
        sections.map((section) => (
          <div key={section.title} className="space-y-3">
            <h4 className="text-sm font-medium text-text-secondary">{section.title}</h4>
            <dl className="grid gap-3 md:grid-cols-2">
              {section.items.map((item) => (
                <div key={`${section.title}-${item.label}`} className="panel-muted space-y-1 p-4">
                  <dt className="text-xs uppercase tracking-[0.18em] text-text-secondary">
                    {item.label}
                  </dt>
                  <dd className="text-sm leading-6 text-text-primary">{item.value}</dd>
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
      <h3 className="font-serif text-lg font-semibold">已采用内容</h3>
      <div className="space-y-3">
        {answers.map((answer) => (
          <article key={`${answer.variable}-${answer.field_path}`} className="rounded-2xl bg-muted p-4">
            <p className="text-xs tracking-[0.12em] text-text-secondary">
              已写入：{formatSettingFieldLabel(answer.field_path)}
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
      <h3 className="font-serif text-lg font-semibold">未采用内容</h3>
      <div className="space-y-3">
        {answers.map((answer) => (
          <article key={`${answer.variable}-${answer.reason}`} className="rounded-2xl bg-muted p-4">
            <p className="mt-2 text-sm leading-6">{answer.value}</p>
            <p className="mt-1 text-xs text-accent-warning">
              这条内容暂未写入草稿，可调整后重试。
            </p>
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
      <ul className="space-y-2 text-sm leading-6 text-text-secondary">
        {questions.map((question) => (
          <li key={question} className="rounded-2xl bg-muted px-4 py-3">
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
      ? "bg-accent-warning/14 text-accent-warning"
      : "bg-accent-info-soft text-accent-info";

  return <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{message}</div>;
}

function PlaceholderCard({
  title,
  description,
  message,
}: {
  title: string;
  description?: string;
  message: string;
}) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold">{title}</h3>
      {description ? <p className="text-sm leading-6 text-text-secondary">{description}</p> : null}
      <p className="rounded-2xl bg-muted px-4 py-3 text-sm leading-6 text-text-secondary">
        {message}
      </p>
    </section>
  );
}
