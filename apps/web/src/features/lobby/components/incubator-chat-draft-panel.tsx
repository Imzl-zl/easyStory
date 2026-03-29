"use client";

import type { UseMutationResult } from "@tanstack/react-query";

import type {
  ProjectDetail,
  ProjectIncubatorConversationDraft,
} from "@/lib/api/types";

import type { IncubatorConversationDraftMutation } from "./incubator-page-model-support";
import { buildSettingSections } from "./incubator-page-support";
import {
  ActionCard,
  DraftBody,
} from "./incubator-chat-draft-panel-support";

type IncubatorChatDraftPanelProps = {
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draft: ProjectIncubatorConversationDraft | null;
  draftMutation: IncubatorConversationDraftMutation;
  hasUserMessage: boolean;
  isDraftStale: boolean;
  onProjectNameChange: (value: string) => void;
  onSyncDraft: () => Promise<void>;
  projectName: string;
};

export function IncubatorChatDraftPanel({
  createMutation,
  draft,
  draftMutation,
  hasUserMessage,
  isDraftStale,
  onProjectNameChange,
  onSyncDraft,
  projectName,
}: Readonly<IncubatorChatDraftPanelProps>) {
  const sections = draft ? buildSettingSections(draft.project_setting) : [];

  return (
    <aside className="order-2 flex min-h-0 flex-col gap-2 lg:order-1 lg:h-full">
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
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
        <DraftBody draft={draft} hasUserMessage={hasUserMessage} sections={sections} />
      </div>
    </aside>
  );
}
