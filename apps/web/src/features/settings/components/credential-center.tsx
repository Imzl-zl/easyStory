"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionCard } from "@/components/ui/section-card";
import { showAppNotice } from "@/components/ui/app-notice";
import {
  resolvePendingCredentialAction,
  type PendingCredentialAction,
} from "@/features/settings/components/credential-center-action-support";
import { CredentialCenterContent } from "@/features/settings/components/credential-center-content";
import {
  resolveCredentialActionFeedback,
  resolveCredentialActionErrorFeedback,
  type CredentialCenterFeedback,
} from "@/features/settings/components/credential-center-feedback";
import { buildCredentialOverrideInfoByCredentialId } from "@/features/settings/components/credential-center-override-support";
import {
  CredentialModeTabs,
  CredentialScopeTabs,
} from "@/features/settings/components/credential-center-tabs";
import {
  buildCredentialCreatePayload,
  buildCredentialUpdatePayload,
  getCredentialUpdatePayloadSize,
  resolveCredentialEditorState,
  resolveEditableCredential,
  resolveActiveCredentialId,
  type CredentialCenterMode,
  type CredentialFormState,
  type CredentialCenterScope,
} from "@/features/settings/components/credential-center-support";
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

type CredentialCenterProps = {
  headerAction?: React.ReactNode;
  isNavigationPending?: boolean;
  mode?: CredentialCenterMode;
  onModeChange?: (mode: CredentialCenterMode) => void;
  onDirtyChange?: (isDirty: boolean) => void;
  onSelectCredential?: (credentialId: string | null) => void;
  onSelectCredentialForEdit?: (credentialId: string | null) => void;
  onResetEditor?: () => void;
  onScopeChange?: (scope: CredentialCenterScope) => void;
  onSyncCredential?: (credentialId: string | null) => void;
  onSyncCredentialForEdit?: (credentialId: string | null) => void;
  projectId?: string | null;
  scope?: CredentialCenterScope;
  selectedCredentialId?: string | null;
};

export function CredentialCenter({
  projectId,
  scope = "user",
  mode = "list",
  selectedCredentialId = null,
  isNavigationPending = false,
  onModeChange,
  onDirtyChange,
  onScopeChange,
  onSelectCredential,
  onSelectCredentialForEdit,
  onResetEditor,
  onSyncCredential,
  onSyncCredentialForEdit,
  headerAction,
}: CredentialCenterProps) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<CredentialCenterFeedback>(null);
  const [createFormVersion, setCreateFormVersion] = useState(0);
  const [editFormVersion, setEditFormVersion] = useState(0);
  const [savedEditableCredential, setSavedEditableCredential] = useState<CredentialView | null>(null);
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
  const activeCredentialId = resolveActiveCredentialId(query.data, selectedCredentialId);
  const editableCredential = resolveEditableCredential(query.data, selectedCredentialId);
  const activeAuditCredentialId = mode === "audit" ? activeCredentialId : null;
  const overrideInfoByCredentialId = buildCredentialOverrideInfoByCredentialId(
    query.data,
    shouldLoadOverrideHints ? overrideQuery.data : undefined,
  );
  const isEditing = mode === "list" && editableCredential !== null;

  useEffect(() => {
    if (query.data === undefined) {
      return;
    }
    if (mode === "audit") {
      if (selectedCredentialId !== activeCredentialId) {
        onSyncCredential?.(activeCredentialId);
      }
      return;
    }
    if (selectedCredentialId && editableCredential === null) {
      onSyncCredentialForEdit?.(null);
    }
  }, [
    activeCredentialId,
    editableCredential,
    mode,
    onSyncCredential,
    onSyncCredentialForEdit,
    query.data,
    selectedCredentialId,
  ]);
  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["credentials"] }),
      queryClient.invalidateQueries({ queryKey: ["credential-audit"] }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (formState: CredentialFormState) =>
      createCredential(
        buildCredentialCreatePayload({
          formState,
          projectId: scopedProjectId,
          scope,
        }),
      ),
    onSuccess: async () => {
      const message = scope === "project" ? "项目级模型连接已创建。" : "全局模型连接已创建。";
      setFeedback({
        message,
        tone: "info",
      });
      showAppNotice({
        content: message,
        title: scope === "project" ? "项目模型连接" : "全局模型连接",
        tone: "success",
      });
      setCreateFormVersion((current) => current + 1);
      await refresh();
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setFeedback({
        message,
        tone: "danger",
      });
      showAppNotice({
        content: message,
        tone: "danger",
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ credential, formState }: { credential: CredentialView; formState: CredentialFormState }) => {
      const payload = buildCredentialUpdatePayload(credential, formState);
      if (getCredentialUpdatePayloadSize(payload) === 0) {
        throw new Error("没有可保存的改动。");
      }
      return updateCredential(credential.id, payload);
    },
    onSuccess: async (result) => {
      const message = "模型连接已更新。";
      setFeedback({
        message,
        tone: "info",
      });
      showAppNotice({
        content: message,
        title: "模型连接",
        tone: "success",
      });
      setSavedEditableCredential(result);
      setEditFormVersion((current) => current + 1);
      await refresh();
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setFeedback({
        message,
        tone: "danger",
      });
      showAppNotice({
        content: message,
        tone: "danger",
      });
    },
  });

  const actionMutation = useMutation({
    mutationFn: async ({
      type,
      credentialId,
    }: PendingCredentialAction) => {
      if (type === "verify_connection") {
        return verifyCredential(credentialId, "text_probe");
      }
      if (type === "verify_stream_tools") {
        return verifyCredential(credentialId, "tool_continuation_probe", "stream");
      }
      if (type === "verify_buffered_tools") {
        return verifyCredential(credentialId, "tool_continuation_probe", "buffered");
      }
      if (type === "enable") {
        return enableCredential(credentialId);
      }
      if (type === "disable") {
        return disableCredential(credentialId);
      }
      return deleteCredential(credentialId);
    },
    onSuccess: async (result, variables) => {
      const nextFeedback = resolveCredentialActionFeedback(result, variables.type);
      setFeedback(nextFeedback);
      if (nextFeedback) {
        showAppNotice({
          content: nextFeedback.message,
          title: resolveCredentialNoticeTitle(variables.type),
          tone: nextFeedback.tone === "danger" ? "danger" : "success",
        });
      }
      if (variables.type === "delete" && variables.credentialId === selectedCredentialId) {
        if (mode === "audit") {
          onSyncCredential?.(null);
        } else {
          onSyncCredentialForEdit?.(null);
        }
      }
      await refresh();
    },
    onError: (error, variables) => {
      const nextFeedback = resolveCredentialActionErrorFeedback(
        error,
        variables.type,
      );
      setFeedback(nextFeedback);
      if (nextFeedback) {
        showAppNotice({
          content: nextFeedback.message,
          tone: "danger",
        });
      }
    },
  });
  const isFormPending = createMutation.isPending || updateMutation.isPending;
  const isInteractionPending = isNavigationPending || isFormPending || actionMutation.isPending;
  const pendingAction = resolvePendingCredentialAction(actionMutation.isPending, actionMutation.variables);
  const canUseProjectScope = projectId !== null && projectId !== undefined;
  const { activeFormKey, activeInitialState } = resolveCredentialEditorState({
    createFormVersion,
    editFormVersion,
    editableCredential,
    savedEditableCredential,
    scope,
    scopedProjectId,
  });
  const shouldShowEditLoadingState = mode === "list" && selectedCredentialId !== null && query.isLoading;
  const handleModeChange = (nextMode: CredentialCenterMode) => {
    setFeedback(null);
    setSavedEditableCredential(null);
    onModeChange?.(nextMode);
  };
  const handleScopeChange = (nextScope: CredentialCenterScope) => {
    setFeedback(null);
    setSavedEditableCredential(null);
    onScopeChange?.(nextScope);
  };
  const handleAuditSelect = (nextCredentialId: string | null) => {
    setFeedback(null);
    onSelectCredential?.(nextCredentialId);
  };
  const handleEditSelect = (nextCredentialId: string | null) => {
    setFeedback(null);
    setSavedEditableCredential(null);
    onSelectCredentialForEdit?.(nextCredentialId);
  };
  const handleResetEditor = () => {
    setFeedback(null);
    setSavedEditableCredential(null);
    onResetEditor?.();
  };

  return (
    <SectionCard
      title="模型连接"
      description="配置并管理 AI 模型连接。可同时添加多个连接，按项目场景灵活切换。"
      action={headerAction}
    >
      <div className="space-y-4">
        <CredentialScopeTabs
          canUseProjectScope={canUseProjectScope}
          isPending={isInteractionPending}
          projectId={projectId ?? null}
          scope={scope}
          onScopeChange={handleScopeChange}
        />
        <CredentialModeTabs isPending={isInteractionPending} mode={mode} onModeChange={handleModeChange} />
        {query.isLoading ? <p className="text-[13px] text-[var(--text-secondary)]">正在加载模型连接…</p> : null}
        {query.error ? (
          <div className="rounded-xl bg-[rgba(178,65,46,0.12)] px-3.5 py-2.5 text-[13px] leading-5 text-[var(--accent-danger)]">
            读取模型连接失败：{getErrorMessage(query.error)}
          </div>
        ) : null}
        {shouldLoadOverrideHints && overrideQuery.isLoading ? (
          <p className="text-[13px] text-[var(--text-secondary)]">正在检查当前项目是否存在项目级覆盖连接…</p>
        ) : null}
        {shouldLoadOverrideHints && overrideQuery.error ? (
          <div className="rounded-xl bg-[rgba(178,65,46,0.12)] px-3.5 py-2.5 text-[13px] leading-5 text-[var(--accent-danger)]">
            项目级覆盖提示加载失败：{getErrorMessage(overrideQuery.error)}
          </div>
        ) : null}
        <CredentialCenterContent
          activeAuditCredentialId={activeAuditCredentialId}
          activeFormKey={activeFormKey}
          activeInitialState={activeInitialState}
          credentials={query.data}
          editableCredential={editableCredential}
          isFormPending={actionMutation.isPending || isFormPending}
          mode={mode}
          onDirtyChange={onDirtyChange}
          overrideInfoByCredentialId={overrideInfoByCredentialId}
          pendingAction={pendingAction}
          shouldShowEditLoadingState={shouldShowEditLoadingState}
          onAction={(type, credentialId) => actionMutation.mutate({ type, credentialId })}
          onResetEditor={handleResetEditor}
          onStartCreate={handleResetEditor}
          onSelectCredential={handleAuditSelect}
          onSelectCredentialForEdit={handleEditSelect}
          onSubmitCreate={(nextFormState) => {
            setFeedback(null);
            createMutation.mutate(nextFormState);
          }}
          onSubmitUpdate={(credential, nextFormState) => {
            setFeedback(null);
            updateMutation.mutate({
              credential,
              formState: nextFormState,
            });
          }}
        />
      </div>
    </SectionCard>
  );
}

function resolveCredentialNoticeTitle(type: PendingCredentialAction["type"]) {
  if (type === "verify_connection") {
    return "模型连接验证";
  }
  if (type === "verify_stream_tools") {
    return "流式工具验证";
  }
  if (type === "verify_buffered_tools") {
    return "非流工具验证";
  }
  if (type === "enable") {
    return "模型连接状态";
  }
  if (type === "disable") {
    return "模型连接状态";
  }
  return "模型连接";
}
