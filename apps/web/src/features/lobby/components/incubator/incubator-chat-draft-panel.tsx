"use client";

import type { UseMutationResult } from "@tanstack/react-query";

import type {
  ProjectDetail,
  ProjectIncubatorConversationDraft,
} from "@/lib/api/types";

import type { IncubatorConversationDraftMutation } from "@/features/lobby/components/incubator/incubator-page-model-support";
import { buildSettingSections } from "@/features/lobby/components/incubator/incubator-page-support";
import {
  ActionCard,
  DraftBody,
} from "@/features/lobby/components/incubator/incubator-chat-draft-panel-support";

type IncubatorChatDraftPanelProps = {
  canCompleteWithAi: boolean;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draft: ProjectIncubatorConversationDraft | null;
  draftMutation: IncubatorConversationDraftMutation;
  hasUserMessage: boolean;
  isDraftStale: boolean;
  isCompletingWithAi: boolean;
  onCompleteWithAi: () => Promise<void>;
  onProjectNameChange: (value: string) => void;
  onSyncDraft: () => Promise<void>;
  projectName: string;
};

export function IncubatorChatDraftPanel({
  canCompleteWithAi,
  createMutation,
  draft,
  draftMutation,
  hasUserMessage,
  isDraftStale,
  isCompletingWithAi,
  onCompleteWithAi,
  onProjectNameChange,
  onSyncDraft,
  projectName,
}: Readonly<IncubatorChatDraftPanelProps>) {
  const sections = draft ? buildSettingSections(draft.project_setting) : [];

  return (
    <aside className="order-2 flex min-h-0 flex-col gap-2 lg:order-1 lg:h-full">
      <ActionCard
        canCreate={Boolean(draft && projectName.trim()) && !createMutation.isPending}
        canCompleteWithAi={canCompleteWithAi}
        canSyncDraft={hasUserMessage && !draftMutation.isPending}
        createMutation={createMutation}
        draft={draft}
        draftMutation={draftMutation}
        isDraftStale={isDraftStale}
        isCompletingWithAi={isCompletingWithAi}
        onCompleteWithAi={onCompleteWithAi}
        onProjectNameChange={onProjectNameChange}
        onSyncDraft={onSyncDraft}
        projectName={projectName}
      />
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
        <DraftBody draft={draft} hasUserMessage={hasUserMessage} sections={sections} />
      </div>
    </aside>
  );
}
