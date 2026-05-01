"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import {
  createMyAssistantHook,
  deleteMyAssistantHook,
  getMyAssistantHook,
  listMyAssistantAgents,
  listMyAssistantHooks,
  updateMyAssistantHook,
} from "@/lib/api/assistant";
import { listMyAssistantMcpServers } from "@/lib/api/assistant-mcp";
import { getErrorMessage } from "@/lib/api/client";

import { AssistantHookEditor } from "@/features/settings/components/assistant/hooks/assistant-hook-editor";
import {
  buildAssistantHookListDescription,
  buildAssistantHookPayload,
  resolveAssistantHookActionLabel,
  resolveAssistantHookEventLabel,
  type AssistantHookDraft,
} from "@/features/settings/components/assistant/hooks/assistant-hooks-support";

type AssistantHooksPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
};

export function AssistantHooksPanel({ onDirtyChange }: Readonly<AssistantHooksPanelProps>) {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<"create" | "edit">("create");
  const [editorHookId, setEditorHookId] = useState<string | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);

  const listQuery = useQuery({
    queryKey: ["assistant-hooks", "me"],
    queryFn: listMyAssistantHooks,
  });

  const agentListQuery = useQuery({
    queryKey: ["assistant-agents", "hook-options"],
    queryFn: listMyAssistantAgents,
  });

  const mcpListQuery = useQuery({
    queryKey: ["assistant-mcps", "hook-options"],
    queryFn: listMyAssistantMcpServers,
  });

  const detailQuery = useQuery({
    queryKey: ["assistant-hook", editorHookId],
    queryFn: () => getMyAssistantHook(editorHookId ?? ""),
    enabled: editorMode === "edit" && Boolean(editorHookId),
  });

  const orderedHooks = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const enabledCount = orderedHooks.filter((h) => h.enabled).length;

  const agentOptions = useMemo(
    () => (agentListQuery.data ?? []).map((a) => ({ label: a.name, value: a.id })),
    [agentListQuery.data],
  );

  const mcpOptions = useMemo(
    () => (mcpListQuery.data ?? []).map((m) => ({ label: m.name ?? m.id, value: m.id })),
    [mcpListQuery.data],
  );

  const createMutation = useMutation({
    mutationFn: (draft: AssistantHookDraft) => createMyAssistantHook(buildAssistantHookPayload(draft)),
    onSuccess: async () => {
      showAppNotice({ title: "Hooks", content: "新的 Hook 已创建。", tone: "success" });
      setEditorOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["assistant-hooks", "me"] });
    },
    onError: (error) => {
      showAppNotice({ title: "Hooks", content: getErrorMessage(error), tone: "danger" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (draft: AssistantHookDraft) => updateMyAssistantHook(editorHookId ?? "", buildAssistantHookPayload(draft)),
    onSuccess: async () => {
      showAppNotice({ title: "Hooks", content: "Hook 已保存。", tone: "success" });
      setEditorOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["assistant-hooks", "me"] });
    },
    onError: (error) => {
      showAppNotice({ title: "Hooks", content: getErrorMessage(error), tone: "danger" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (hookId: string) => deleteMyAssistantHook(hookId),
    onSuccess: async () => {
      showAppNotice({ title: "Hooks", content: "Hook 已删除。", tone: "success" });
      setEditorOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["assistant-hooks", "me"] });
    },
    onError: (error) => {
      showAppNotice({ title: "Hooks", content: getErrorMessage(error), tone: "danger" });
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  useEffect(() => {
    onDirtyChange?.(editorDirty && editorOpen);
    return () => onDirtyChange?.(false);
  }, [editorDirty, editorOpen, onDirtyChange]);

  const handleCreate = () => {
    setEditorMode("create");
    setEditorHookId(null);
    setEditorOpen(true);
  };

  const handleEdit = (hookId: string) => {
    setEditorMode("edit");
    setEditorHookId(hookId);
    setEditorOpen(true);
  };

  const handleCloseEditor = () => {
    if (editorDirty) {
      showAppNotice({
        title: "Hooks",
        content: "当前 Hook 还有未保存的改动，请先保存或还原。",
        tone: "warning",
      });
      return;
    }
    setEditorOpen(false);
  };

  const selectedDetail = editorMode === "edit" && detailQuery.data ? detailQuery.data : null;

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-canvas)" }}>
      {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent-primary)" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "var(--accent-primary)" }}>
                高级能力
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Hooks
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <StatBadge label="已启用" value={enabledCount} color="var(--accent-success)" />
              <StatBadge label="总计" value={orderedHooks.length} />
            </div>
          </div>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium flex items-center gap-1.5"
            style={{ background: "var(--accent-primary)", color: "var(--text-on-accent)" }}
            disabled={isPending}
            type="button"
            onClick={handleCreate}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            新建 Hook
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto" style={{ scrollbarWidth: "thin", scrollbarColor: "var(--line-medium) transparent" }}>
        <div className="px-6 py-5">
          {listQuery.isLoading ? (
            <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>正在读取 Hooks...</p>
          ) : listQuery.error ? (
            <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {getErrorMessage(listQuery.error)}
            </div>
          ) : orderedHooks.length === 0 ? (
            <EmptyState onCreate={handleCreate} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {orderedHooks.map((hook) => (
                <HookCard
                  key={hook.id}
                  actionType={hook.action.action_type}
                  description={buildAssistantHookListDescription(hook)}
                  enabled={hook.enabled}
                  event={hook.event}
                  name={hook.name}
                  onDelete={() => deleteMutation.mutate(hook.id)}
                  onEdit={() => handleEdit(hook.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Editor Modal */}
      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "var(--overlay-bg)" }}>
          <div className="w-full max-w-[800px] max-h-[90vh] overflow-hidden rounded-lg flex flex-col" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
            {/* Modal Header */}
            <div className="px-5 py-4 flex items-center justify-between flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
              <div>
                <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
                  {editorMode === "create" ? "新建 Hook" : "编辑 Hook"}
                </h2>
                <p className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
                  {editorMode === "create" ? "创建一条自动化规则" : "修改这条规则的触发条件和动作"}
                </p>
              </div>
              <button
                className="w-7 h-7 rounded-md flex items-center justify-center"
                style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
                onClick={handleCloseEditor}
                type="button"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin", scrollbarColor: "var(--line-medium) transparent" }}>
              {editorMode === "edit" && detailQuery.isLoading ? (
                <div className="px-5 py-8 text-center">
                  <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>正在加载 Hook...</p>
                </div>
              ) : editorMode === "edit" && detailQuery.error ? (
                <div className="px-5 py-4">
                  <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
                    {getErrorMessage(detailQuery.error)}
                  </div>
                </div>
              ) : (
                <AssistantHookEditor
                  agentErrorMessage={agentListQuery.error ? getErrorMessage(agentListQuery.error) : null}
                  agentOptions={agentOptions}
                  detail={selectedDetail}
                  isPending={isPending}
                  mode={editorMode}
                  mcpErrorMessage={mcpListQuery.error ? getErrorMessage(mcpListQuery.error) : null}
                  mcpOptions={mcpOptions}
                  onDelete={editorMode === "edit" ? () => {
                    if (editorHookId) deleteMutation.mutate(editorHookId);
                    setEditorOpen(false);
                  } : undefined}
                  onDirtyChange={setEditorDirty}
                  onSubmit={(draft) => {
                    if (editorMode === "create") {
                      createMutation.mutate(draft);
                    } else {
                      updateMutation.mutate(draft);
                    }
                  }}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatBadge({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span className="text-[13px] font-semibold" style={{ color: color || "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

function HookCard({
  actionType,
  description,
  enabled,
  event,
  name,
  onDelete,
  onEdit,
}: {
  actionType: "agent" | "mcp";
  description: string;
  enabled: boolean;
  event: "before_assistant_response" | "after_assistant_response";
  name: string;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div
      className="rounded-lg p-4 transition-colors hover:brightness-110"
      style={{
        background: "var(--bg-canvas)",
        border: "1px solid var(--line-soft)",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{
              background: enabled ? "var(--accent-success)" : "var(--text-tertiary)",
              boxShadow: enabled ? "0 0 6px #22c55e40" : "none",
            }}
          />
          <span className="text-[13px] font-medium truncate" style={{ color: "var(--text-primary)" }}>
            {name}
          </span>
        </div>
        <span
          className="text-[9px] px-1.5 py-0.5 rounded font-medium flex-shrink-0"
          style={{
            background: enabled ? "var(--accent-success-soft)" : "rgba(75,85,99,0.2)",
            color: enabled ? "var(--accent-success)" : "var(--text-tertiary)",
          }}
        >
          {enabled ? "启用" : "停用"}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}>
          {resolveAssistantHookEventLabel(event)}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)" }}>
          {resolveAssistantHookActionLabel(actionType)}
        </span>
      </div>
      <p className="mt-2 text-[11px] leading-4 line-clamp-2" style={{ color: "var(--text-tertiary)" }}>
        {description}
      </p>
      <div className="flex gap-2 mt-3">
        <button
          className="h-7 px-3 rounded text-[11px] font-medium"
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          onClick={onEdit}
          type="button"
        >
          编辑
        </button>
        <button
          className="h-7 px-3 rounded text-[11px] font-medium"
          style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
          onClick={onDelete}
          type="button"
        >
          删除
        </button>
      </div>
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-12 h-12 rounded-full flex items-center justify-center mb-4" style={{ background: "var(--bg-muted)" }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
      </div>
      <p className="text-[14px] font-medium" style={{ color: "var(--text-secondary)" }}>还没有 Hook</p>
      <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>创建你的第一条自动化规则</p>
      <button
        className="mt-4 h-8 px-4 rounded-md text-[12px] font-medium"
        style={{ background: "var(--accent-primary)", color: "var(--text-on-accent)" }}
        onClick={onCreate}
        type="button"
      >
        新建 Hook
      </button>
    </div>
  );
}
