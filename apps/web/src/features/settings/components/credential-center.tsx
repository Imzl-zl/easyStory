"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionCard } from "@/components/ui/section-card";
import {
  resolvePendingCredentialAction,
  type PendingCredentialAction,
} from "@/features/settings/components/credential-center-action-support";
import { CredentialCenterContent } from "@/features/settings/components/credential-center-content";
import {
  resolveCredentialActionFeedback,
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
  createCredentialFormFromView,
  createInitialCredentialForm,
  getCredentialUpdatePayloadSize,
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
  projectId?: string | null;
  scope?: CredentialCenterScope;
  mode?: CredentialCenterMode;
  selectedCredentialId?: string | null;
  isNavigationPending?: boolean;
  onModeChange?: (mode: CredentialCenterMode) => void;
  onScopeChange?: (scope: CredentialCenterScope) => void;
  onSelectCredential?: (credentialId: string | null) => void;
  onSelectCredentialForEdit?: (credentialId: string | null) => void;
  onResetEditor?: () => void;
  headerAction?: React.ReactNode;
};

export function CredentialCenter({
  projectId,
  scope = "user",
  mode = "list",
  selectedCredentialId = null,
  isNavigationPending = false,
  onModeChange,
  onScopeChange,
  onSelectCredential,
  onSelectCredentialForEdit,
  onResetEditor,
  headerAction,
}: CredentialCenterProps) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<CredentialCenterFeedback>(null);
  const [createFormVersion, setCreateFormVersion] = useState(0);
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
        onSelectCredential?.(activeCredentialId);
      }
      return;
    }
    if (selectedCredentialId && editableCredential === null) {
      onSelectCredentialForEdit?.(null);
    }
  }, [
    activeCredentialId,
    editableCredential,
    mode,
    onSelectCredential,
    onSelectCredentialForEdit,
    query.data,
    selectedCredentialId,
  ]);

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
      setFeedback({
        message: scope === "project" ? "项目级模型连接已创建。" : "全局模型连接已创建。",
        tone: "info",
      });
      setCreateFormVersion((current) => current + 1);
      await refresh();
    },
    onError: (error) =>
      setFeedback({
        message: getErrorMessage(error),
        tone: "danger",
      }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ credential, formState }: { credential: CredentialView; formState: CredentialFormState }) => {
      const payload = buildCredentialUpdatePayload(credential, formState);
      if (getCredentialUpdatePayloadSize(payload) === 0) {
        throw new Error("没有可保存的改动。");
      }
      return updateCredential(credential.id, payload);
    },
    onSuccess: async (updatedCredential) => {
      setFeedback({
        message: "模型连接已更新。",
        tone: "info",
      });
      onSelectCredentialForEdit?.(updatedCredential.id);
      await refresh();
    },
    onError: (error) =>
      setFeedback({
        message: getErrorMessage(error),
        tone: "danger",
      }),
  });

  const actionMutation = useMutation({
    mutationFn: async ({
      type,
      credentialId,
    }: PendingCredentialAction) => {
      if (type === "verify") {
        return verifyCredential(credentialId);
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
      setFeedback(resolveCredentialActionFeedback(result, variables.type));
      if (variables.type === "delete" && variables.credentialId === selectedCredentialId) {
        if (mode === "audit") {
          onSelectCredential?.(null);
        } else {
          onSelectCredentialForEdit?.(null);
        }
      }
      await refresh();
    },
    onError: (error) =>
      setFeedback({
        message: getErrorMessage(error),
        tone: "danger",
      }),
  });
  const isFormPending = createMutation.isPending || updateMutation.isPending;
  const isInteractionPending = isNavigationPending || isFormPending || actionMutation.isPending;
  const pendingAction = resolvePendingCredentialAction(actionMutation.isPending, actionMutation.variables);
  const canUseProjectScope = projectId !== null && projectId !== undefined;
  const createFormKey = `create:${scope}:${scopedProjectId ?? "global"}:${createFormVersion}`;
  const activeFormKey = isEditing && editableCredential ? `edit:${editableCredential.id}` : createFormKey;
  const activeInitialState = editableCredential ? createCredentialFormFromView(editableCredential) : createInitialCredentialForm();
  const shouldShowEditLoadingState = mode === "list" && selectedCredentialId !== null && query.isLoading;
  const handleModeChange = (nextMode: CredentialCenterMode) => {
    setFeedback(null);
    onModeChange?.(nextMode);
  };
  const handleScopeChange = (nextScope: CredentialCenterScope) => {
    setFeedback(null);
    onScopeChange?.(nextScope);
  };
  const handleAuditSelect = (nextCredentialId: string | null) => {
    setFeedback(null);
    onSelectCredential?.(nextCredentialId);
  };
  const handleEditSelect = (nextCredentialId: string | null) => {
    setFeedback(null);
    onSelectCredentialForEdit?.(nextCredentialId);
  };
  const handleResetEditor = () => {
    setFeedback(null);
    onResetEditor?.();
  };

  return (
    <SectionCard
      title="模型连接"
      description="配置并管理 AI 模型连接。可同时添加多个连接，按项目场景灵活切换。"
      action={headerAction}
    >
      <div className="space-y-5">
        <CredentialScopeTabs
          canUseProjectScope={canUseProjectScope}
          isPending={isInteractionPending}
          projectId={projectId ?? null}
          scope={scope}
          onScopeChange={handleScopeChange}
        />
        <CredentialModeTabs isPending={isInteractionPending} mode={mode} onModeChange={handleModeChange} />
        {query.isLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载模型连接...</p> : null}
        {query.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            {getErrorMessage(query.error)}
          </div>
        ) : null}
        {shouldLoadOverrideHints && overrideQuery.isLoading ? (
          <p className="text-sm text-[var(--text-secondary)]">正在检查当前项目是否存在项目级覆盖连接...</p>
        ) : null}
        {shouldLoadOverrideHints && overrideQuery.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            项目级覆盖提示加载失败：{getErrorMessage(overrideQuery.error)}
          </div>
        ) : null}
        <CredentialCenterContent
          activeAuditCredentialId={activeAuditCredentialId}
          activeFormKey={activeFormKey}
          activeInitialState={activeInitialState}
          credentials={query.data}
          editableCredential={editableCredential}
          feedback={feedback}
          isFormPending={actionMutation.isPending || isFormPending}
          mode={mode}
          overrideInfoByCredentialId={overrideInfoByCredentialId}
          pendingAction={pendingAction}
          shouldShowEditLoadingState={shouldShowEditLoadingState}
          onAction={(type, credentialId) => actionMutation.mutate({ type, credentialId })}
          onResetEditor={handleResetEditor}
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
