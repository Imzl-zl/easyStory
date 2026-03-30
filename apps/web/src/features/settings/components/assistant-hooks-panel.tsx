"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
import {
  createMyAssistantHook,
  deleteMyAssistantHook,
  getMyAssistantHook,
  listMyAssistantAgents,
  listMyAssistantHooks,
  listMyAssistantMcpServers,
  updateMyAssistantHook,
} from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import type { AssistantHookDetail, AssistantHookSummary, AssistantMcpSummary } from "@/lib/api/types";

import { AssistantHookEditor } from "./assistant-hook-editor";
import {
  buildAssistantHookListDescription,
  buildAssistantHookPayload,
  type AssistantHookDraft,
} from "./assistant-hooks-support";

const CREATE_MODE_KEY = "__create-hook__";

type AssistantHooksPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
};

export function AssistantHooksPanel({ onDirtyChange }: AssistantHooksPanelProps) {
  const queryClient = useQueryClient();
  const [requestedSelection, setRequestedSelection] = useState<string | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const listQuery = useQuery({ queryKey: ["assistant-hooks", "me"], queryFn: listMyAssistantHooks });
  const agentListQuery = useQuery({ queryKey: ["assistant-agents", "hook-options"], queryFn: listMyAssistantAgents });
  const mcpListQuery = useQuery({ queryKey: ["assistant-mcp", "hook-options"], queryFn: listMyAssistantMcpServers });
  const orderedHooks = useMemo(
    () => [...(listQuery.data ?? [])].sort((left, right) => right.updated_at?.localeCompare(left.updated_at ?? "") ?? -1),
    [listQuery.data],
  );
  const selection = resolveHookSelection(requestedSelection, orderedHooks);
  const detailQuery = useQuery({
    enabled: selection !== CREATE_MODE_KEY,
    queryKey: ["assistant-hooks", selection],
    queryFn: () => getMyAssistantHook(selection),
  });

  const invalidateHooks = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["assistant-hooks"] }),
    queryClient.invalidateQueries({ queryKey: ["assistant-hooks", "chat-selector"] }),
  ]);
  const createMutation = useMutation({
    mutationFn: (draft: AssistantHookDraft) => createMyAssistantHook(buildAssistantHookPayload(draft)),
    onSuccess: async (detail) => {
      await invalidateHooks();
      setRequestedSelection(detail.id);
      showAppNotice({ title: "Hooks", content: "已创建 Hook。", tone: "success" });
    },
    onError: (error) => showAppNotice({ title: "Hooks", content: getErrorMessage(error), tone: "danger" }),
  });
  const updateMutation = useMutation({
    mutationFn: (draft: AssistantHookDraft) => updateMyAssistantHook(selection, buildAssistantHookPayload(draft)),
    onSuccess: async (detail) => {
      await invalidateHooks();
      queryClient.setQueryData(["assistant-hooks", detail.id], detail);
      showAppNotice({ title: "Hooks", content: "已保存 Hook。", tone: "success" });
    },
    onError: (error) => showAppNotice({ title: "Hooks", content: getErrorMessage(error), tone: "danger" }),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteMyAssistantHook,
    onSuccess: async () => {
      await invalidateHooks();
      setRequestedSelection(null);
      showAppNotice({ title: "Hooks", content: "已删除 Hook。", tone: "success" });
    },
    onError: (error) => showAppNotice({ title: "Hooks", content: getErrorMessage(error), tone: "danger" }),
  });

  return (
    <HooksPanelBody
      agentErrorMessage={agentListQuery.error ? getErrorMessage(agentListQuery.error) : null}
      agentOptions={buildAgentOptions(agentListQuery.data ?? [])}
      detail={selection === CREATE_MODE_KEY ? null : detailQuery.data ?? null}
      editorDirty={editorDirty}
      hooks={orderedHooks}
      isPending={createMutation.isPending || updateMutation.isPending || deleteMutation.isPending}
      mcpErrorMessage={mcpListQuery.error ? getErrorMessage(mcpListQuery.error) : null}
      mcpOptions={buildMcpOptions(mcpListQuery.data ?? [])}
      onCreate={() => attemptHookSelection(CREATE_MODE_KEY, editorDirty, setRequestedSelection)}
      onDelete={(hookId) => deleteMutation.mutate(hookId)}
      onDirtyChange={(isDirty) => {
        setEditorDirty(isDirty);
        onDirtyChange?.(isDirty);
      }}
      onSelect={(hookId) => attemptHookSelection(hookId, editorDirty, setRequestedSelection)}
      onSubmit={(draft) => (selection === CREATE_MODE_KEY ? createMutation.mutate(draft) : updateMutation.mutate(draft))}
      selection={selection}
    />
  );
}

function HooksPanelBody({
  agentErrorMessage,
  agentOptions,
  detail,
  editorDirty,
  hooks,
  isPending,
  mcpErrorMessage,
  mcpOptions,
  onCreate,
  onDelete,
  onDirtyChange,
  onSelect,
  onSubmit,
  selection,
}: Readonly<{
  agentErrorMessage: string | null;
  agentOptions: { label: string; value: string; description?: string }[];
  detail: AssistantHookDetail | null;
  editorDirty: boolean;
  hooks: AssistantHookSummary[];
  isPending: boolean;
  mcpErrorMessage: string | null;
  mcpOptions: { label: string; value: string; description?: string }[];
  onCreate: () => void;
  onDelete: (hookId: string) => void;
  onDirtyChange: (isDirty: boolean) => void;
  onSelect: (hookId: string) => void;
  onSubmit: (draft: AssistantHookDraft) => void;
  selection: string;
}>) {
  const agentLabelMap = new Map(agentOptions.map((item) => [item.value, item.label]));
  const mcpLabelMap = new Map(mcpOptions.map((item) => [item.value, item.label]));
  const enabledHookCount = hooks.filter((hook) => hook.enabled).length;
  const showCreateEditor = selection === CREATE_MODE_KEY;

  return (
    <SectionCard
      description="你的自动动作配置。把回复前后的额外步骤保存下来，需要时再打开。"
      title="Hooks"
    >
      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="space-y-3 rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] p-4 xl:sticky xl:top-6 xl:self-start">
          <div className="space-y-1 rounded-[18px] bg-[rgba(248,243,235,0.78)] px-4 py-3">
            <p className="text-sm font-medium text-[var(--text-primary)]">我的 Hooks</p>
            <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
              已启用 {enabledHookCount} 个，共 {hooks.length} 个。
            </p>
          </div>
          <button className="ink-button w-full justify-center" disabled={isPending} type="button" onClick={onCreate}>
            新建 Hook
          </button>
          <div className="space-y-2 xl:max-h-[28rem] xl:overflow-y-auto xl:pr-1">
            {hooks.map((hook) => (
              <button
                className="ink-tab w-full justify-start rounded-[20px] px-4 py-3 text-left"
                data-active={selection === hook.id}
                key={hook.id}
                type="button"
                onClick={() => onSelect(hook.id)}
              >
                <span className="flex flex-col items-start gap-1">
                  <span className="text-sm font-medium text-[var(--text-primary)]">{hook.name}</span>
                  <span className="text-[12px] leading-5 text-[var(--text-secondary)]">
                    {buildAssistantHookListDescription(hook, {
                      agentLabel: hook.action.action_type === "agent" ? agentLabelMap.get(hook.action.agent_id) ?? null : null,
                      mcpLabel: hook.action.action_type === "mcp" ? mcpLabelMap.get(hook.action.server_id) ?? null : null,
                    })}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </aside>
        <div className="space-y-4">
          {showCreateEditor && hooks.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-[var(--line-soft)] bg-[rgba(255,255,255,0.6)] px-5 py-6 text-sm leading-7 text-[var(--text-secondary)]">
              先创建一个 Hook。比如“回复后自动整理”，这样每次回复完都能自动多做一步；不需要自动化时可以先跳过。
            </div>
          ) : null}
          {showCreateEditor || detail ? (
            <AssistantHookEditor
              agentErrorMessage={agentErrorMessage}
              agentOptions={agentOptions}
              detail={detail}
              isPending={isPending}
              key={showCreateEditor ? CREATE_MODE_KEY : `${detail?.id ?? "empty"}:${detail?.updated_at ?? ""}`}
              mcpErrorMessage={mcpErrorMessage}
              mcpOptions={mcpOptions}
              mode={showCreateEditor ? "create" : "edit"}
              onDelete={detail ? () => onDelete(detail.id) : undefined}
              onDirtyChange={onDirtyChange}
              onSubmit={onSubmit}
            />
          ) : null}
          {!showCreateEditor && !detail && !editorDirty ? (
            <div className="rounded-[24px] border border-dashed border-[var(--line-soft)] bg-[rgba(255,255,255,0.6)] px-5 py-6 text-sm leading-7 text-[var(--text-secondary)]">
              请选择一个 Hook 查看详情。
            </div>
          ) : null}
        </div>
      </div>
    </SectionCard>
  );
}

function buildAgentOptions(agents: Awaited<ReturnType<typeof listMyAssistantAgents>>) {
  return agents.map((agent) => ({
    description: agent.enabled ? undefined : "已停用，但 Hook 仍可继续绑定使用",
    label: agent.enabled ? agent.name : `${agent.name}（已停用）`,
    value: agent.id,
  }));
}

function buildMcpOptions(mcpServers: AssistantMcpSummary[]) {
  return mcpServers.map((server) => ({
    description: server.enabled ? server.url : "已停用，暂时不能在聊天里执行",
    label: server.enabled ? server.name : `${server.name}（已停用）`,
    value: server.id,
  }));
}

function attemptHookSelection(
  nextSelection: string,
  isDirty: boolean,
  setSelection: (value: string) => void,
) {
  if (isDirty) {
    showAppNotice({
      title: "Hooks",
      content: "当前 Hook 还有未保存的改动，请先保存或还原。",
      tone: "warning",
    });
    return;
  }
  setSelection(nextSelection);
}

function resolveHookSelection(
  requestedSelection: string | null,
  hooks: AssistantHookSummary[],
) {
  if (requestedSelection === CREATE_MODE_KEY) {
    return CREATE_MODE_KEY;
  }
  if (requestedSelection && hooks.some((item) => item.id === requestedSelection)) {
    return requestedSelection;
  }
  return hooks[0]?.id ?? CREATE_MODE_KEY;
}
