"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
import { getErrorMessage } from "@/lib/api/client";

import { AssistantSkillEditor } from "@/features/settings/components/assistant/skills/assistant-skill-editor";
import {
  buildAssistantSkillDetailQueryKey,
  buildAssistantSkillListQueryKey,
  buildAssistantSkillsPanelCopy,
  createAssistantSkill,
  deleteAssistantSkill,
  loadAssistantSkillDetail,
  loadAssistantSkills,
  type AssistantSkillsPanelCopy,
  updateAssistantSkill,
} from "@/features/settings/components/assistant/skills/assistant-skills-panel-support";
import {
  buildAssistantSkillListDescription,
  buildAssistantSkillPayload,
  type AssistantSkillDraft,
} from "@/features/settings/components/assistant/skills/assistant-skills-support";

type AssistantSkillsPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
  projectId?: string;
  scope?: "project" | "user";
};

const CREATE_MODE_KEY = "__create__";

export function AssistantSkillsPanel({
  onDirtyChange,
  projectId,
  scope = "user",
}: Readonly<AssistantSkillsPanelProps>) {
  const copy = buildAssistantSkillsPanelCopy(scope);
  const queryClient = useQueryClient();
  const [requestedSelection, setRequestedSelection] = useState<string | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const listQuery = useQuery({
    queryKey: buildAssistantSkillListQueryKey(scope, projectId),
    queryFn: () => loadAssistantSkills(scope, projectId),
  });
  const orderedSkills = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const selection = useMemo(() => {
    if (requestedSelection === CREATE_MODE_KEY) {
      return CREATE_MODE_KEY;
    }
    if (requestedSelection && orderedSkills.some((item) => item.id === requestedSelection)) {
      return requestedSelection;
    }
    if (listQuery.isLoading) {
      return null;
    }
    return orderedSkills[0]?.id ?? CREATE_MODE_KEY;
  }, [listQuery.isLoading, orderedSkills, requestedSelection]);
  const detailQuery = useQuery({
    queryKey: buildAssistantSkillDetailQueryKey(scope, projectId, selection),
    queryFn: () => loadAssistantSkillDetail(scope, projectId, selection ?? ""),
    enabled: Boolean(selection) && selection !== CREATE_MODE_KEY,
  });
  const createMutation = useMutation({
    mutationFn: (draft: AssistantSkillDraft) =>
      createAssistantSkill(scope, projectId, buildAssistantSkillPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: copy.title, content: copy.createSuccess, tone: "success" });
      setRequestedSelection(detail.id);
      await queryClient.invalidateQueries({ queryKey: buildAssistantSkillListQueryKey(scope, projectId) });
      await queryClient.invalidateQueries({
        queryKey: buildAssistantSkillDetailQueryKey(scope, projectId, detail.id),
      });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });
  const updateMutation = useMutation({
    mutationFn: (draft: AssistantSkillDraft) =>
      updateAssistantSkill(scope, projectId, selection ?? "", buildAssistantSkillPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: copy.title, content: copy.saveSuccess, tone: "success" });
      await queryClient.invalidateQueries({ queryKey: buildAssistantSkillListQueryKey(scope, projectId) });
      await queryClient.invalidateQueries({
        queryKey: buildAssistantSkillDetailQueryKey(scope, projectId, detail.id),
      });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (skillId: string) => deleteAssistantSkill(scope, projectId, skillId),
    onSuccess: async () => {
      showAppNotice({ title: copy.title, content: copy.deleteSuccess, tone: "success" });
      setRequestedSelection(null);
      await queryClient.invalidateQueries({ queryKey: buildAssistantSkillListQueryKey(scope, projectId) });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });
  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  const selectedDetail = selection === CREATE_MODE_KEY ? null : detailQuery.data ?? null;
  const showCreateEditor = selection === CREATE_MODE_KEY;
  const enabledSkillCount = orderedSkills.filter((skill) => skill.enabled).length;
  const showGettingStarted = showCreateEditor && orderedSkills.length === 0;

  useEffect(() => {
    onDirtyChange?.(editorDirty);
    return () => onDirtyChange?.(false);
  }, [editorDirty, onDirtyChange]);

  return (
    <SectionCard description={copy.description} title={copy.title}>
      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="space-y-3 rounded-3xl bg-glass shadow-glass p-4 xl:sticky xl:top-6 xl:self-start">
          <div className="space-y-1 rounded-2xl bg-muted px-4 py-3">
            <p className="text-sm font-medium text-text-primary">{copy.summaryLabel}</p>
            <p className="text-[12px] leading-5 text-text-secondary">
              已启用 {enabledSkillCount} 个，共 {orderedSkills.length} 个。
            </p>
          </div>
          <button
            className="ink-button w-full justify-center"
            disabled={isPending}
            type="button"
            onClick={() => attemptSelect(CREATE_MODE_KEY, editorDirty, setRequestedSelection, copy)}
          >
            新建 Skill
          </button>
          <div className="space-y-2 xl:max-h-[28rem] xl:overflow-y-auto xl:pr-1">
            {orderedSkills.map((skill) => (
              <button
                className="ink-tab w-full justify-start rounded-2xl px-4 py-3 text-left"
                data-active={selection === skill.id}
                key={skill.id}
                type="button"
                onClick={() => attemptSelect(skill.id, editorDirty, setRequestedSelection, copy)}
              >
                <span className="flex flex-col items-start gap-1">
                  <span className="text-sm font-medium text-text-primary">{skill.name}</span>
                  <span className="text-[12px] leading-5 text-text-secondary">
                    {buildAssistantSkillListDescription(skill)}
                  </span>
                </span>
              </button>
            ))}
            {listQuery.isLoading ? (
              <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{copy.listLoading}</div>
            ) : null}
            {listQuery.error ? (
              <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
                {getErrorMessage(listQuery.error)}
              </div>
            ) : null}
            {showGettingStarted ? (
              <div className="rounded-2xl bg-glass px-4 py-4 text-sm leading-6 text-text-secondary">
                {copy.emptyHint}
              </div>
            ) : null}
          </div>
        </aside>
        <div className="space-y-4">
          {listQuery.isLoading && !selection ? (
            <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{copy.createHint}</div>
          ) : null}
          {showCreateEditor ? (
            <AssistantSkillEditor
              key={CREATE_MODE_KEY}
              detail={null}
              isPending={isPending}
              mode="create"
              onDirtyChange={setEditorDirty}
              onSubmit={(draft) => createMutation.mutate(draft)}
            />
          ) : null}
          {!showCreateEditor && detailQuery.isLoading && selection ? (
            <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{copy.detailLoading}</div>
          ) : null}
          {!showCreateEditor && detailQuery.error ? (
            <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
              {getErrorMessage(detailQuery.error)}
            </div>
          ) : null}
          {!showCreateEditor && selectedDetail ? (
            <AssistantSkillEditor
              key={`${selectedDetail.id}:${selectedDetail.updated_at ?? ""}`}
              detail={selectedDetail}
              isPending={isPending}
              mode="edit"
              onDelete={() => deleteMutation.mutate(selectedDetail.id)}
              onDirtyChange={setEditorDirty}
              onSubmit={(draft) => updateMutation.mutate(draft)}
            />
          ) : null}
        </div>
      </div>
    </SectionCard>
  );
}

function attemptSelect(
  nextSelection: string,
  isDirty: boolean,
  setSelection: (value: string) => void,
  copy: AssistantSkillsPanelCopy,
) {
  if (isDirty) {
    showAppNotice({
      title: copy.title,
      content: copy.dirtyMessage,
      tone: "warning",
    });
    return;
  }
  setSelection(nextSelection);
}
