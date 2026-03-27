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
    <aside className="space-y-4 xl:sticky xl:top-6">
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
      <DraftBody draft={draft} hasUserMessage={hasUserMessage} sections={sections} />
    </aside>
  );
}
