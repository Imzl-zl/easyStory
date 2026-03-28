"use client";

import type { UseMutationResult } from "@tanstack/react-query";

import type {
  ProjectDetail,
  ProjectIncubatorConversationDraft,
} from "@/lib/api/types";

import { buildSettingSections } from "./incubator-page-support";
import {
  ActionCard,
  DraftBody,
} from "./incubator-chat-draft-panel-support";

type IncubatorChatDraftPanelProps = {
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  hasUserMessage: boolean;
  isDraftStale: boolean;
  onProjectNameChange: (value: string) => void;
  onSyncDraft: () => Promise<void>;
  projectName: string;
};

export function IncubatorChatDraftPanel({
  createMutation,
  draftMutation,
  hasUserMessage,
  isDraftStale,
  onProjectNameChange,
  onSyncDraft,
  projectName,
}: Readonly<IncubatorChatDraftPanelProps>) {
  const draft = draftMutation.data;
  const sections = draft ? buildSettingSections(draft.project_setting) : [];

  return (
    <aside className="order-2 flex min-h-0 flex-col gap-2.5 lg:order-1 lg:h-full">
      <ActionCard
        canCreate={Boolean(draft && projectName.trim()) && !createMutation.isPending}
        canSyncDraft={hasUserMessage && !draftMutation.isPending}
        createMutation={createMutation}
        draft={draft}
        draftMutation={draftMutation}
        isDraftStale={isDraftStale}
        onProjectNameChange={onProjectNameChange}
        onSyncDraft={onSyncDraft}
        projectName={projectName}
      />
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pr-0.5">
        <DraftBody draft={draft} hasUserMessage={hasUserMessage} sections={sections} />
      </div>
    </aside>
  );
}
