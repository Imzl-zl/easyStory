"use client";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import {
  resolvePendingCredentialAction,
  type PendingCredentialAction,
} from "@/features/settings/components/credential/credential-center-action-support";
import {
  CredentialCenterList,
  type CredentialListItemData,
} from "@/features/settings/components/credential/credential-center-list";
import { CredentialHealthPanel } from "@/features/settings/components/credential/credential-health-panel";
import { CredentialAuditTimeline } from "@/features/settings/components/credential/credential-audit-timeline";
import { CredentialEditorModal } from "@/features/settings/components/credential/credential-editor-modal";
import {
  resolveCredentialActionFeedback,
  resolveCredentialActionErrorFeedback,
} from "@/features/settings/components/credential/credential-center-feedback";
import { buildCredentialOverrideInfoByCredentialId } from "@/features/settings/components/credential/credential-center-override-support";
import {
  CredentialScopeTabs,
} from "@/features/settings/components/credential/credential-center-tabs";
import {
  buildCredentialCreatePayload,
  buildCredentialUpdatePayload,
  getCredentialUpdatePayloadSize,
  resolveCredentialEditorState,
  resolveEditableCredential,
  resolveActiveCredentialId,
  createInitialCredentialForm,
  type CredentialCenterScope,
  type CredentialFormState,
} from "@/features/settings/components/credential/credential-center-support";
import {
  createCredential,
  deleteCredential,
  disableCredential,
  enableCredential,
  listCredentials,
  updateCredential,
  verifyCredential,
} from "@/lib/api/credential";
import { getErrorMessage } from "@/lib/api/client";
import type { CredentialView } from "@/lib/api/types";

type ViewMode = "list" | "health" | "audit";

export function CredentialCenter({
  projectId,
  scope = "user",
  selectedCredentialId = null,
  isNavigationPending = false,
  onDirtyChange,
  onScopeChange,
  onSyncCredentialForEdit,
}: {
  projectId?: string | null;
  scope?: CredentialCenterScope;
  selectedCredentialId?: string | null;
  isNavigationPending?: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
  onScopeChange?: (scope: CredentialCenterScope) => void;
  onSyncCredentialForEdit?: (credentialId: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [selectedId, setSelectedId] = useState<string | null>(selectedCredentialId);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<"create" | "edit">("create");
  const [editorCredential, setEditorCredential] = useState<CredentialView | null>(null);

  const scopedProjectId = scope === "project" ? projectId ?? null : null;
  const shouldLoadOverrideHints = scope === "user" && projectId !== null && projectId !== undefined;

  const query = useQuery({
    queryKey: ["credentials", scope, scopedProjectId],
    queryFn: () => listCredentials(scope, scopedProjectId ?? undefined),
  });

  const overrideQuery = useQuery({
    enabled: shouldLoadOverrideHints,
    queryKey: ["credentials", "project", projectId ?? null, "override-hints"],
    queryFn: () => listCredentials("project", projectId as string),
  });

  const credentials = query.data ?? [];
  const overrideInfoByCredentialId = buildCredentialOverrideInfoByCredentialId(
    query.data,
    shouldLoadOverrideHints ? overrideQuery.data : undefined,
  );

  // Stats
  const stats = useMemo(() => {
    const total = credentials.length;
    const active = credentials.filter((c) => c.is_active).length;
    const withIssues = credentials.filter((c) => {
      const caps = (c as any).capabilities;
      const stream = caps?.stream;
      const buffered = caps?.buffered;
      const streamOk = stream?.connection_verified && stream?.tools_verified;
      const bufferedOk = buffered?.connection_verified && buffered?.tools_verified;
      return c.is_active && (!streamOk || !bufferedOk);
    }).length;
    return { total, active, withIssues };
  }, [credentials]);

  // Selected credential
  const selectedCredential = useMemo(
    () => credentials.find((c) => c.id === selectedId) ?? null,
    [credentials, selectedId],
  );

  useEffect(() => {
    if (selectedCredentialId && !credentials.find((c) => c.id === selectedCredentialId)) {
      onSyncCredentialForEdit?.(null);
    }
  }, [credentials, selectedCredentialId, onSyncCredentialForEdit]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["credentials"] }),
      queryClient.invalidateQueries({ queryKey: ["credential-audit"] }),
    ]);
  };

  // Mutations
  const createMutation = useMutation({
    mutationFn: (formState: CredentialFormState) =>
      createCredential(buildCredentialCreatePayload({ formState, projectId: scopedProjectId, scope })),
    onSuccess: async () => {
      showAppNotice({ content: scope === "project" ? "项目级模型连接已创建。" : "全局模型连接已创建。", title: "模型连接", tone: "success" });
      setEditorOpen(false);
      await refresh();
    },
    onError: (error) => showAppNotice({ content: getErrorMessage(error), tone: "danger" }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ credential, formState }: { credential: CredentialView; formState: CredentialFormState }) => {
      const payload = buildCredentialUpdatePayload(credential, formState);
      if (getCredentialUpdatePayloadSize(payload) === 0) throw new Error("没有可保存的改动。");
      return updateCredential(credential.id, payload);
    },
    onSuccess: async () => {
      showAppNotice({ content: "模型连接已更新。", title: "模型连接", tone: "success" });
      setEditorOpen(false);
      await refresh();
    },
    onError: (error) => showAppNotice({ content: getErrorMessage(error), tone: "danger" }),
  });

  const actionMutation = useMutation({
    mutationFn: async ({ type, credentialId }: PendingCredentialAction) => {
      if (type === "verify_stream_connection") return verifyCredential(credentialId, "text_probe", "stream");
      if (type === "verify_buffered_connection") return verifyCredential(credentialId, "text_probe", "buffered");
      if (type === "verify_stream_tools") return verifyCredential(credentialId, "tool_continuation_probe", "stream");
      if (type === "verify_buffered_tools") return verifyCredential(credentialId, "tool_continuation_probe", "buffered");
      if (type === "enable") return enableCredential(credentialId);
      if (type === "disable") return disableCredential(credentialId);
      return deleteCredential(credentialId);
    },
    onSuccess: async (result, variables) => {
      const nextFeedback = resolveCredentialActionFeedback(result, variables.type);
      if (nextFeedback) showAppNotice({ content: nextFeedback.message, title: "模型连接", tone: nextFeedback.tone === "danger" ? "danger" : "success" });
      if (variables.type === "delete" && variables.credentialId === selectedId) setSelectedId(null);
      await refresh();
    },
    onError: (error, variables) => {
      const nextFeedback = resolveCredentialActionErrorFeedback(error, variables.type);
      if (nextFeedback) showAppNotice({ content: nextFeedback.message, tone: "danger" });
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending || actionMutation.isPending || isNavigationPending;
  const pendingAction = resolvePendingCredentialAction(actionMutation.isPending, actionMutation.variables);
  const canUseProjectScope = projectId !== null && projectId !== undefined;

  const listItems: CredentialListItemData[] = useMemo(() =>
    credentials.map((c) => ({
      id: c.id,
      name: c.display_name,
      provider: c.provider,
      dialect: c.api_dialect,
      model: c.default_model,
      isActive: c.is_active,
      isSelected: c.id === selectedId,
      overrideInfo: overrideInfoByCredentialId[c.id],
      streamStatus: getConnectionStatus(c, "stream"),
      bufferedStatus: getConnectionStatus(c, "buffered"),
    })),
  [credentials, selectedId, overrideInfoByCredentialId]);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    if (viewMode === "list") setViewMode("health");
  };

  const handleEdit = (credential: CredentialView) => {
    setEditorMode("edit");
    setEditorCredential(credential);
    setEditorOpen(true);
  };

  const handleCreate = () => {
    setEditorMode("create");
    setEditorCredential(null);
    setEditorOpen(true);
  };

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-canvas)" }}>
      {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent-primary)" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "var(--accent-primary)" }}>
                基础设施
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              模型连接
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <StatBadge label="总计" value={stats.total} />
              <StatBadge label="正常" value={stats.active - stats.withIssues} color="var(--accent-success)" />
              {stats.withIssues > 0 && <StatBadge label="异常" value={stats.withIssues} color="var(--accent-danger)" />}
            </div>
          </div>
          <button
            className="ink-button h-8 text-[12px]"
            onClick={handleCreate}
            disabled={isPending}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            添加连接
          </button>
        </div>

        {/* Scope + View Tabs */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: "var(--bg-muted)" }}>
            <CredentialScopeTabs
              canUseProjectScope={canUseProjectScope}
              isPending={isPending}
              projectId={projectId ?? null}
              scope={scope}
              onScopeChange={onScopeChange}
            />
          </div>
          <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: "var(--bg-muted)" }}>
            {(["list", "health", "audit"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                className="px-3 py-1.5 rounded-md text-[11px] font-medium transition-all"
                onClick={() => setViewMode(mode)}
                style={{
                  background: viewMode === mode ? "var(--bg-elevated)" : "transparent",
                  color: viewMode === mode ? "var(--text-primary)" : "var(--text-tertiary)",
                }}
              >
                {mode === "list" ? "连接列表" : mode === "health" ? "健康面板" : "审计日志"}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto" style={{ scrollbarWidth: "thin", scrollbarColor: "var(--line-medium) transparent" }}>
        <div className="px-6 py-5">
          {query.isLoading ? (
            <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>正在加载模型连接…</p>
          ) : query.error ? (
            <div className="rounded-lg px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              读取模型连接失败：{getErrorMessage(query.error)}
            </div>
          ) : credentials.length === 0 ? (
            <EmptyState onCreate={handleCreate} />
          ) : viewMode === "list" ? (
            <CredentialCenterList
              items={listItems}
              onSelect={handleSelect}
              onEdit={(id) => {
                const c = credentials.find((x) => x.id === id);
                if (c) handleEdit(c);
              }}
              onAction={(type, id) => actionMutation.mutate({ type, credentialId: id })}
              pendingAction={pendingAction}
              isPending={isPending}
            />
          ) : viewMode === "health" ? (
            <CredentialHealthPanel
              credential={selectedCredential}
              credentials={credentials}
              onSelect={handleSelect}
              onVerify={(type, id) => actionMutation.mutate({ type, credentialId: id })}
              onToggle={(id) => {
                const c = credentials.find((x) => x.id === id);
                if (c) actionMutation.mutate({ type: c.is_active ? "disable" : "enable", credentialId: id });
              }}
              onEdit={(id) => {
                const c = credentials.find((x) => x.id === id);
                if (c) handleEdit(c);
              }}
              pendingAction={pendingAction}
              isPending={isPending}
            />
          ) : (
            <CredentialAuditTimeline
              credentialId={selectedId}
              credentials={credentials}
              onSelectCredential={setSelectedId}
            />
          )}
        </div>
      </div>

      {/* Editor Modal */}
      {editorOpen && (
        <CredentialEditorModal
          mode={editorMode}
          credential={editorCredential}
          isPending={createMutation.isPending || updateMutation.isPending}
          onClose={() => setEditorOpen(false)}
          onSubmit={(formState) => {
            if (editorMode === "edit" && editorCredential) {
              updateMutation.mutate({ credential: editorCredential, formState });
            } else {
              createMutation.mutate(formState);
            }
          }}
        />
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

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-12 h-12 rounded-full flex items-center justify-center mb-4" style={{ background: "var(--bg-muted)" }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round">
          <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
          <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
        </svg>
      </div>
      <p className="text-[14px] font-medium" style={{ color: "var(--text-secondary)" }}>还没有模型连接</p>
      <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>添加你的第一个模型 API 连接</p>
      <button
        className="ink-button mt-4 h-8 text-[12px]"
        onClick={onCreate}
      >
        添加连接
      </button>
    </div>
  );
}

function getConnectionStatus(c: CredentialView, transport: "stream" | "buffered"): "ok" | "warning" | "error" | "unknown" {
  const cap = (c as any).capabilities?.[transport];
  if (!cap) return "unknown";
  if (cap.connection_verified && cap.tools_verified) return "ok";
  if (cap.connection_verified || cap.tools_verified) return "warning";
  return "error";
}
