"use client";

import type { ProjectIncubatorConversationDraft } from "@/lib/api/types";

import { buildDraftGuidance } from "@/features/lobby/components/incubator/incubator-chat-draft-support";

type DraftGuidanceCardProps = {
  canCompleteWithAi: boolean;
  draft: ProjectIncubatorConversationDraft;
  isCompletingWithAi: boolean;
  onCompleteWithAi: () => void;
};

export function DraftGuidanceCard({
  canCompleteWithAi,
  draft,
  isCompletingWithAi,
  onCompleteWithAi,
}: Readonly<DraftGuidanceCardProps>) {
  const guidance = buildDraftGuidance(draft);

  return (
    <section className="panel-muted space-y-2 p-3">
      <div className="space-y-1">
        <p className="text-[11px] font-medium text-text-primary">{guidance.summary}</p>
        <p className="text-[12px] leading-5 text-text-secondary">{guidance.detail}</p>
      </div>
      {guidance.actionLabel ? (
        <button
          className="ink-button-secondary"
          disabled={!canCompleteWithAi}
          type="button"
          onClick={onCompleteWithAi}
        >
          {isCompletingWithAi ? "AI 补全中…" : guidance.actionLabel}
        </button>
      ) : null}
    </section>
  );
}
