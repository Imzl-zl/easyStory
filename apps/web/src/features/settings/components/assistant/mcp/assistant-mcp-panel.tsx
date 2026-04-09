"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
import { getErrorMessage } from "@/lib/api/client";

import { AssistantMcpEditor } from "@/features/settings/components/assistant/mcp/assistant-mcp-editor";
import {
  buildAssistantMcpDetailQueryKey,
  buildAssistantMcpListQueryKey,
  buildAssistantMcpPanelCopy,
  createAssistantMcp,
  deleteAssistantMcp,
  loadAssistantMcpDetail,
  loadAssistantMcpServers,
  type AssistantMcpPanelCopy,
  updateAssistantMcp,
} from "@/features/settings/components/assistant/mcp/assistant-mcp-panel-support";
import {
  buildAssistantMcpListDescription,
  buildAssistantMcpPayload,
  type AssistantMcpDraft,
} from "@/features/settings/components/assistant/mcp/assistant-mcp-support";

type AssistantMcpPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
  projectId?: string;
  scope?: "project" | "user";
};

const CREATE_MODE_KEY = "__create-mcp__";

export function AssistantMcpPanel({
  onDirtyChange,
  projectId,
  scope = "user",
}: Readonly<AssistantMcpPanelProps>) {
  const copy = buildAssistantMcpPanelCopy(scope);
  const queryClient = useQueryClient();
  const [requestedSelection, setRequestedSelection] = useState<string | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const listQuery = useQuery({
    queryKey: buildAssistantMcpListQueryKey(scope, projectId),
    queryFn: () => loadAssistantMcpServers(scope, projectId),
  });
  const orderedMcpServers = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const selection = useMemo(() => {
    if (requestedSelection === CREATE_MODE_KEY) {
      return CREATE_MODE_KEY;
    }
    if (requestedSelection && orderedMcpServers.some((item) => item.id === requestedSelection)) {
      return requestedSelection;
    }
    if (listQuery.isLoading) {
      return null;
    }
    return orderedMcpServers[0]?.id ?? CREATE_MODE_KEY;
  }, [listQuery.isLoading, orderedMcpServers, requestedSelection]);
  const detailQuery = useQuery({
    queryKey: buildAssistantMcpDetailQueryKey(scope, projectId, selection),
    queryFn: () => loadAssistantMcpDetail(scope, projectId, selection ?? ""),
    enabled: Boolean(selection) && selection !== CREATE_MODE_KEY,
  });
  const createMutation = useMutation({
    mutationFn: (draft: AssistantMcpDraft) =>
      createAssistantMcp(scope, projectId, buildAssistantMcpPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: copy.title, content: copy.createSuccess, tone: "success" });
      setRequestedSelection(detail.id);
      await queryClient.invalidateQueries({ queryKey: buildAssistantMcpListQueryKey(scope, projectId) });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });
  const updateMutation = useMutation({
    mutationFn: (draft: AssistantMcpDraft) =>
      updateAssistantMcp(scope, projectId, selection ?? "", buildAssistantMcpPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: copy.title, content: copy.saveSuccess, tone: "success" });
      await queryClient.invalidateQueries({ queryKey: buildAssistantMcpListQueryKey(scope, projectId) });
      queryClient.setQueryData(buildAssistantMcpDetailQueryKey(scope, projectId, detail.id), detail);
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (serverId: string) => deleteAssistantMcp(scope, projectId, serverId),
    onSuccess: async () => {
      showAppNotice({ title: copy.title, content: copy.deleteSuccess, tone: "success" });
      setRequestedSelection(null);
      await queryClient.invalidateQueries({ queryKey: buildAssistantMcpListQueryKey(scope, projectId) });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });
  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  const selectedDetail = selection === CREATE_MODE_KEY ? null : detailQuery.data ?? null;
  const showCreateEditor = selection === CREATE_MODE_KEY;
  const enabledCount = orderedMcpServers.filter((item) => item.enabled).length;

  useEffect(() => {
    onDirtyChange?.(editorDirty);
    return () => onDirtyChange?.(false);
  }, [editorDirty, onDirtyChange]);

  return (
    <SectionCard description={copy.description} title={copy.title}>
      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="space-y-3 rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] p-4 xl:sticky xl:top-6 xl:self-start">
          <div className="space-y-1 rounded-[18px] bg-[rgba(248,243,235,0.78)] px-4 py-3">
            <p className="text-sm font-medium text-[var(--text-primary)]">{copy.summaryLabel}</p>
            <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
              已启用 {enabledCount} 个，共 {orderedMcpServers.length} 个。
            </p>
          </div>
          <button
            className="ink-button w-full justify-center"
            disabled={isPending}
            type="button"
            onClick={() => attemptMcpSelect(CREATE_MODE_KEY, editorDirty, setRequestedSelection, copy)}
          >
            新建 MCP
          </button>
          <div className="space-y-2 xl:max-h-[28rem] xl:overflow-y-auto xl:pr-1">
            {orderedMcpServers.map((server) => (
              <button
                className="ink-tab w-full justify-start rounded-[20px] px-4 py-3 text-left"
                data-active={selection === server.id}
                key={server.id}
                type="button"
                onClick={() => attemptMcpSelect(server.id, editorDirty, setRequestedSelection, copy)}
              >
                <span className="flex flex-col items-start gap-1">
                  <span className="text-sm font-medium text-[var(--text-primary)]">{server.name}</span>
                  <span className="text-[12px] leading-5 text-[var(--text-secondary)]">
                    {buildAssistantMcpListDescription(server)}
                  </span>
                </span>
              </button>
            ))}
            {listQuery.isLoading ? (
              <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{copy.listLoading}</div>
            ) : null}
            {listQuery.error ? (
              <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
                {getErrorMessage(listQuery.error)}
              </div>
            ) : null}
          </div>
        </aside>
        <div className="space-y-4">
          {showCreateEditor ? (
            <AssistantMcpEditor
              key={CREATE_MODE_KEY}
              detail={null}
              isPending={isPending}
              mode="create"
              onDirtyChange={setEditorDirty}
              onSubmit={(draft) => createMutation.mutate(draft)}
            />
          ) : null}
          {!showCreateEditor && detailQuery.isLoading && selection ? (
            <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{copy.detailLoading}</div>
          ) : null}
          {!showCreateEditor && detailQuery.error ? (
            <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
              {getErrorMessage(detailQuery.error)}
            </div>
          ) : null}
          {!showCreateEditor && selectedDetail ? (
            <AssistantMcpEditor
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

function attemptMcpSelect(
  nextSelection: string,
  isDirty: boolean,
  setSelection: (value: string) => void,
  copy: AssistantMcpPanelCopy,
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
