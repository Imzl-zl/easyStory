"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import {
  buildProjectSettingIssueSummary,
  buildProjectSettingSections,
} from "@/features/project/components/project-setting-summary-support";
import type { ProjectIncubatorConversationDraft } from "@/lib/api/types";

type ProjectSettingSummaryPreviewProps = {
  draft: ProjectIncubatorConversationDraft;
};

export function ProjectSettingSummaryPreview({
  draft,
}: Readonly<ProjectSettingSummaryPreviewProps>) {
  const sections = buildProjectSettingSections(draft.project_setting);
  const summary = buildProjectSettingIssueSummary(
    draft.setting_completeness,
    "摘要已经覆盖主要信息，可以直接保存。",
  );

  return (
    <section className="space-y-4 rounded-2xl border border-accent-primary-muted bg-muted p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-text-primary">提炼结果预览</p>
          <p className="text-sm leading-6 text-text-secondary">{summary}</p>
        </div>
        <StatusBadge status={draft.setting_completeness.status} />
      </div>
      {draft.follow_up_questions.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.18em] text-text-secondary">
            建议继续补充
          </p>
          <ul className="space-y-2 text-sm leading-6 text-text-secondary">
            {draft.follow_up_questions.map((question) => (
              <li key={question}>• {question}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="grid gap-3 xl:grid-cols-2">
        {sections.map((section) => (
          <div
            key={section.title}
            className="rounded-2xl bg-surface shadow-sm p-4"
          >
            <p className="font-medium text-text-primary">{section.title}</p>
            <dl className="mt-3 space-y-2">
              {section.items.map((item) => (
                <div
                  key={`${section.title}-${item.label}`}
                  className="grid gap-1 md:grid-cols-[84px_minmax(0,1fr)]"
                >
                  <dt className="text-sm text-text-secondary">{item.label}</dt>
                  <dd className="text-sm leading-6 text-text-primary">{item.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
